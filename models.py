# Deep Helmholtz Decomposition
# Andrew Sosanya, Sam Greydanus | 2020

import torch
import torch.nn as nn

class MLP(nn.Module): 
    def __init__(self, input_dim, output_dim, hidden_dim):
      super(MLP, self).__init__()
      self.lin_1 = nn.Linear(input_dim, hidden_dim)
      self.lin_2 = nn.Linear(hidden_dim, output_dim)
    
    def forward(self, x):
      h = self.lin_1(x).tanh() 
      y_hat = self.lin_2(h)
      return y_hat


class HHD(nn.Module): 
  def __init__(self, input_dim, hidden_dim):
    super(HHD, self).__init__()  # Inherit the methods of the Module constructor
    self.mlp_h = MLP(input_dim, 1, hidden_dim)  # Instantiate an MLP for learning the conservative component
    self.mlp_d = MLP(input_dim, 1, hidden_dim)  # Instantiate an MLP for learning the dissipative component
    
  def forward(self, x, rho=None, as_separate=False): 
    inputs = torch.cat([x, rho], axis=-1) if rho is not None else x
    D = self.mlp_d(inputs)
    H = self.mlp_h(inputs)

    irr_component = torch.autograd.grad(D.sum(), x, create_graph=True)[0]  # Take their gradients
    rot_component = torch.autograd.grad(H.sum(), x, create_graph=True)[0]

    # For H, we need the symplectic gradient, and therefore
    #   we split our tensor into 2 and swap the chunks.
    dHdq, dHdp = torch.split(rot_component, rot_component.shape[-1]//2, dim=1)
    q_dot_hat, p_dot_hat = dHdp, -dHdq
    rot_component = torch.cat([q_dot_hat, p_dot_hat], axis=-1)
    if as_separate:
        return irr_component, rot_component  # Return the two fields seperately, or return the composite field. 

    return irr_component + rot_component  # return decomposition if as_separate else sum of fields


class HNN(nn.Module): 
  def __init__(self, input_dim, hidden_dim):
    super(HNN, self).__init__()  # Inherit the methods of the Module constructor
    self.mlp = MLP(input_dim, 1, hidden_dim)  # Instantiate an instance of our baseline model.
    
  def forward(self, x): 
    output = self.mlp(x)  # Bx2 Get the scalars from our baseline model

    H = output[...,0]  # Separate out the Dissapative (D) and Hamiltonian (H) functions
    H_grads = torch.autograd.grad(H.sum(), x, create_graph=True)[0]

    # For H, we need the symplectic gradient, and therefore
    #   we split our tensor into 2 and swap the chunks.
    dHdq, dHdp = torch.split(H_grads, H_grads.shape[-1]//2, dim=1)
    q_dot_hat, p_dot_hat = dHdp, -dHdq
    H_hat = torch.cat([q_dot_hat, p_dot_hat], axis=-1)
    return H_hat