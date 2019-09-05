import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.utils.data as data
import torchvision.models as models
from torchvision import datasets, transforms
from matplotlib import pyplot as plt


BATCH_SIZE = 4
NUM_WORKERS = 2
LR = 1e-3

data_folder = "./cats_and_dogs"

traindir = os.path.join(data_folder, 'train')
testdir = os.path.join(data_folder, 'test')

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

torch.manual_seed(31415926)
if 'cuda' in str(device):
    torch.cuda.manual_seed(31415926)


normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

train_loader = data.DataLoader(
    datasets.ImageFolder(traindir,
                         transforms.Compose([
                             transforms.RandomResizedCrop(224),
                             transforms.RandomHorizontalFlip(),
                             transforms.ToTensor(),
                             normalize,
                         ])),
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=NUM_WORKERS,
    pin_memory=False)


# Definition here: https://github.com/pytorch/vision/blob/master/torchvision/models/resnet.py
model = models.resnet50(pretrained=True)

# Don't train the normal layers
for param in model.parameters():
    param.requires_grad = False

# Create a new output layer
model.fc = nn.Linear(2048, 2) # New layers has requires_grad = True by default

model = model.to(device)

forward_grad = None
def printnorm_forward(self, input_, output):
    global forward_grad
    # input is a tuple of packed inputs
    # output is a Tensor.
    print('Inside ' + self.__class__.__name__ + ' forward')
    print('')
    print('input: ', type(input_))
    print('input[0]: ', type(input_[0]))
    print('output: ', type(output))
    print('output[0]: ', type(output[0]))
    print('')
    print('input size:', input_[0].size())
    print('output size:', output.size())
    print('output norm:', output.norm())

    forward_grad = input_[0].detach().cpu().numpy()


backward_grad = None
def printnorm_backward(self, input_, output):
    global backward_grad
    # input is a tuple of packed inputs
    # output is a Tensor.
    print('Inside ' + self.__class__.__name__ + ' backward')
    print('')
    print('input: ', type(input_))
    print('input[0]: ', type(input_[0]))
    print('output: ', type(output))
    print('output[0]: ', type(output[0]))
    print('')
    print('input size:', input_[0].size())
    print('output size:', len(output))
    print('output[0] size:', output[0].size())
    print('output norm:', output[0].norm())

    backward_grad = input_[0].detach().cpu().numpy()


# This could be useful for using the features produced by a pretrained network
# If all you care about is this feature vector, then use a Variable with volatile=True to speed up inference
model.fc.register_forward_hook(printnorm_forward)
# This could be useful to analyse the gradient of a pretrained network
model.fc.register_backward_hook(printnorm_backward)


optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=LR)


def train(epoch):
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        print(data.shape)
        data, target = data.to(device), target.to(device)
        data.requires_grad = True
        optimizer.zero_grad()
        output = model(data)
        loss = F.cross_entropy(output, target)
        loss.backward()
        optimizer.step()

        # Display the gradients
        plt.clf()
        plt.subplot(211); plt.hist(forward_grad.ravel()); plt.title("Features magnitude")
        plt.subplot(212); plt.hist(backward_grad.ravel()); plt.title("Gradients")
        plt.tight_layout()
        plt.show(block=False)
        plt.pause(0.01)

        print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
            epoch, batch_idx * len(data), len(train_loader.dataset),
            100. * batch_idx / len(train_loader), loss.item()))


if __name__ == '__main__':
    for epoch in range(1, 2):
        train(epoch)
