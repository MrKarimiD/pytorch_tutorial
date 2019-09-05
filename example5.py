import os
import random
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.utils.data as data
from torchvision import datasets, transforms

random.seed(31415926)

BATCH_SIZE = 16
NUM_WORKERS = 1
LR = 1e-3

data_folder = "cats_and_dogs"

traindir = os.path.join(data_folder, 'train')
testdir = os.path.join(data_folder, 'test')

if not os.path.isdir(traindir):
    raise Exception('Please download the cats and dogs dataset and put it '
                    'into the ./cats_and_dogs/ folder.')

# Change the folder structure of the dataset, if ran for the first time
if not os.path.isdir(os.path.join(traindir, "cat")):
    print("Reorganizing the dataset...")
    from glob import glob
    import shutil
    from itertools import product
    for folder in product([traindir, testdir], ["cat", "dog"]):
        os.makedirs(os.path.join(*folder), exist_ok=True)
    for f in glob(os.path.join(traindir, "*.jpg")):
        folder, rest = f.split(".", maxsplit=1)
        if random.random() < 0.04:
            folder = folder.replace(traindir, testdir)
        shutil.move(f, os.path.join(folder, rest))


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
    num_workers=NUM_WORKERS)
test_loader = data.DataLoader(
    datasets.ImageFolder(testdir,
                         transforms.Compose([
                             transforms.RandomResizedCrop(224),
                             transforms.RandomHorizontalFlip(),
                             transforms.ToTensor(),
                             normalize,
                         ])),
    batch_size=200,
    shuffle=True,
    num_workers=NUM_WORKERS)


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(3, 10, kernel_size=5)
        self.conv2 = nn.Conv2d(10, 20, kernel_size=5)
        self.bn2 = nn.BatchNorm2d(20)
        self.conv3 = nn.Conv2d(20, 30, kernel_size=5)
        self.bn3 = nn.BatchNorm2d(30)
        self.conv4 = nn.Conv2d(30, 30, kernel_size=5, stride=2)
        self.bn4 = nn.BatchNorm2d(30)
        self.fc1 = nn.Linear(750, 256)
        self.fc2 = nn.Linear(256, 2)

    def forward(self, x):
        x = F.elu(F.max_pool2d(self.conv1(x), 2))
        x = F.elu(F.max_pool2d(self.bn2(self.conv2(x)), 2))
        x = F.elu(F.max_pool2d(self.bn3(self.conv3(x)), 2))
        x = F.elu(F.max_pool2d(self.bn4(self.conv4(x)), 2))

        x = x.view(-1, 750)
        x = F.relu(self.fc1(x))
        x = F.dropout(x, training=self.training)
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)


model = Net()
model = model.to(device)
optimizer = optim.Adam(model.parameters(), lr=LR)


def train(epoch):
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = F.cross_entropy(output, target)
        loss.backward()
        optimizer.step()
        print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
            epoch, batch_idx * len(data), len(train_loader.dataset),
            100. * batch_idx / len(train_loader), loss.item()))


def test():
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for batch_idx, (data, target) in enumerate(test_loader):
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.cross_entropy(output, target, reduction='sum').item() # sum up batch loss
            pred = output.data.max(1)[1] # get the index of the max log-probability
            correct += pred.eq(target.data.view_as(pred)).cpu().sum()

    test_loss /= len(test_loader.dataset)
    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        test_loss, correct, len(test_loader.dataset),
        100. * correct / len(test_loader.dataset)))


if __name__ == '__main__':
    for epoch in range(1, 3):
        train(epoch)
    print("Running test...")
    test()
    # 1 epoch gives 66% accuracy in 12 minutes on CPU
