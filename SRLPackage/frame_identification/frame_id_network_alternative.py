import torch
import torch.nn as nn
import torchvision.datasets as dsets
import torchvision.transforms as transforms
from torch.autograd import Variable
import torchtext
from torchtext import data
from torchtext import vocab
import pandas as pd 

from reader import Data_reader

use_cuda = True

#The files generated by pyfn
train_file = ["../data/experiments/xp_001/data/train.sentences", "../data/experiments/xp_001/data/train.frame.elements"]
dev_file = ["../data/experiments/xp_001/data/dev.sentences", "../data/experiments/xp_001/data/dev.frames"]
test_file = ["../data/experiments/xp_001/data/test.sentences", "../data/experiments/xp_001/data/test.frames"]


def prepare_dataset(file):
    reader = Data_reader(file[0], file[1])
    reader.read_data()
    dataset = reader.get_dataset()

    xs = [[i[4]]+i[0] for i in dataset]
    
    ys = [i[1] for i in dataset]

    return xs, ys

xs, ys = prepare_dataset(train_file)

dev_xs, dev_ys = prepare_dataset(dev_file)

dataset_size = len(xs)

input_field = data.Field(dtype=torch.float, use_vocab=True, preprocessing=None)#, fix_length= max_length) #No padding necessary anymore, since avg

output_field = data.Field(dtype=torch.long)
data_fields = [('Sentence', input_field), ('Frame', output_field)]

examples = [data.Example.fromlist([x,y], data_fields) for x,y in zip(xs,ys)]

dev_examples = [data.Example.fromlist([x,y], data_fields) for x,y in zip(dev_xs,dev_ys)]

my_dataset = data.Dataset(examples, fields=data_fields)

dev_dataset = data.Dataset(dev_examples, fields=data_fields)


input_field.build_vocab(my_dataset)

input_field.build_vocab(dev_dataset)
output_field.build_vocab(my_dataset)

batch_size = 1

train_iter = data.BucketIterator(my_dataset, batch_size=batch_size, shuffle=False)
dev_iter = data.BucketIterator(dev_dataset, batch_size=batch_size, shuffle=False)


input_field.vocab.load_vectors("glove.6B.300d")


print(len(output_field.vocab))

input_count = len(input_field.vocab)



hidden_size = 2048
hidden_size2 = 1024
num_classes = len(output_field.vocab)
num_epochs = 2
learning_rate = 0.001
embedding_size = 300


embed = nn.Embedding.from_pretrained(input_field.vocab.vectors)

def average_sentence(sent):
    """ Averages a sentence/multiple sentences by taking the mean of its embeddings

        Args:
            sent: the given sentence as numbers from the vocab

        Returns:
            the averaged sentence/sentences as a tensor (size equals the size of one word embedding for each sentence)

    """

    lookup_tensor = torch.tensor(sent, dtype=torch.long)
    embedded_sent = embed(lookup_tensor)

    #Skip first vector, as it does not belong to the senctence
    #print(len(sent))
    #print(embedded_sent[1])
    #embedded_sent
    #exit()

    averaged_sent = embedded_sent.mean(dim=0)

    #Reappend the FEE 
    #print(embedded_sent[0][0])
    #exit()

    appended_avg = []

    for sentence in averaged_sent:
        inc_FEE = torch.cat((embedded_sent[0][0], sentence),0)
        appended_avg.append(inc_FEE)
        #print(inc_FEE)
        #exit()

    #averaged_sent = torch.cat((embedded_sent[0], averaged_sent),0)
    #print(len(averaged_sent))
    #exit()
    #print(averaged_sent.shape)
    averaged_sent = torch.stack(appended_avg)
    #print(averaged_sent.shape)
    #exit()

    return averaged_sent




#Create network
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()

        self.fc1 = nn.Linear(embedding_size * 2, hidden_size) 
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, hidden_size2) 
        self.relu2 = nn.ReLU()
        self.fc3 = nn.Linear(hidden_size2, num_classes)  
    
    def forward(self, x):

        x = Variable(average_sentence(x)).to(device)

        out = self.fc1(x)
        out = self.relu(out)
        out = self.fc2(out)
        out = self.relu2(out)
        out = self.fc3(out)
        return out

#Check for CUDA
use_cuda = use_cuda and torch.cuda.is_available()
device = torch.device("cuda" if use_cuda else "cpu")    
print(device)

net = Net()

net.to(device)   

# Loss and Optimizer
criterion = nn.CrossEntropyLoss()  
optimizer = torch.optim.Adam(net.parameters(), lr=learning_rate)  

def train_model():
    """ Trains the model with the training dataset
        
        - uses the model specified in net 

    """
    for epoch in range(num_epochs):   
        #Counter for the iterations
        i = 0

        for batch in iter(train_iter):
            
            sent = batch.Sentence
            sent = torch.tensor(sent, dtype=torch.long)
            
            
            #sent = Variable(average_sentence(sent)).to(device)
            labels = Variable(batch.Frame[0]).to(device)

            
            # Forward + Backward + Optimize
            optimizer.zero_grad()  # zero the gradient buffer
            outputs = net(sent)

            loss = criterion(outputs,labels)
            loss.backward()
            optimizer.step()
            
            if (i+1) % 100 == 0:
                print ('Epoch [%d/%d], Step [%d/%d], Loss: %.4f' 
                       %(epoch+1, num_epochs, i+1, dataset_size//batch_size, loss.data[0]))

            i += 1


def eval_model():
    """ Evaluates the model on the development dataset

        Args:

        Returns:
            The accuracy reached on the development dataset

    """
    correct = 0.0
    total = 0.0
    for batch in iter(dev_iter):
        sent = batch.Sentence
        sent = torch.tensor(sent, dtype=torch.long)
        labels = Variable(batch.Frame[0]).to(device)

        outputs = net(sent)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum()
        
    correct = int(correct.data[0])

    #print(correct)
    #print(total)
    accuracy = correct/total

    return accuracy

train_model()
acc =eval_model()
print(acc)
