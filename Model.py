import torch
from torch import  nn

class MoCo(nn.Module):
    def __init__(self,backbone,m,queue):
        super(MoCo,self).__init__()

        self.keys_encoder= backbone #todo: change backbone
        self.query_encoder= backbone
        self.m= m
        self.queue_ptr= 0
        _,self.queue_size= self.queue.shape
        self.queue = nn.functional.normalize(self.queue, dim=0)

        for param_q, param_k in zip(self.query_encoder.parameters(), self.keys_encoder.parameters()):
            param_k.data.copy_(param_q.data)  # initialize
            param_k.requires_grad = False  # not update by gradient

    def forward(self, x_k,x_q,Train=True):
        ''' Augment x twice -> pass through k/q networks -> '''

        q= self.query_encoder(x_q)
        q = nn.functional.normalize(q, dim=1)

        with torch.no_grad():
            if Train:
                self._momentum_contrast_update()

            k= self.keys_encoder(x_k)
            k = nn.functional.normalize(k, dim=1)

        N,C= k.shape#shape of input data (NxC)
        _,K= self.queue.shape

        #Create Logits
        l_pos= torch.bmm(q.view(N,1,C),k.view(N,C,1)).squeeze(-1) #dim (Nx1)
        l_neg= torch.mm(q.view(N,C),self.queue.clone().detach().view(C,K)) #dim (NxK)

        logits= torch.cat((l_pos,l_neg),dim=1) #dim (Nx(K+1))

        if Train:
            self._UpdateQueue(keys=k)

        return logits,k

    def _momentum_contrast_update(self):
        for theta_q, theta_k in zip(self.query_encoder.parameters(),
                                    self.keys_encoder.parameters()):  # TODO:vectorize

            c = theta_k.data.sum()
            # print(c)
            a = (1. - self.m) * theta_q.data
            b = self.m * theta_k.data
            # print(a.sum())
            # print(b.sum())
            theta_k.data = theta_k.data * self.m + theta_q.data * (1. - self.m)
            # print(theta_k.data.sum())
            # if c!= a.sum()+b.sum():
            #     p=[]

    def _UpdateQueue(self,keys):
        N, C = keys.shape
        ''' ========  Enqueue/Dequeue  ======== '''
        self.queue[:, self.queue_ptr:self.queue_ptr + N] = keys.T
        self.queue_ptr = (self.queue_ptr + N)%self.queue_size # move pointer

class DownStreamTaskModel(nn.Module):
    def __init__(self,encoder):
        super(DownStreamTaskModel,self).__init__()

        self.encoder= encoder
        self.fc= nn.Sequential(nn.Linear(),nn.ReLU(),nn.Dropout())

    def forward(self,batch):
        return self.fc(self.encoder(batch))
