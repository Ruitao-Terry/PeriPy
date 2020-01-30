"""
Created on Sun Nov 10 16:25:58 2019

@author: Ben Boys
"""

import numpy as np
import pathlib
from peridynamics.grid import Grid
from peridynamics import Model
import time


class SimpleSquare(Model):
    # A user defined class for a particular problem which defines all necessary
    # parameters

    def __init__(self):
        super().__init__()
        self.dim = 2

        # Material parameters from classical material model
        self.horizon = 0.1
        self.kscalar = 0.05
        self.s00 = 0.005

        self.crack_length = 0.3

        mesh_file = pathlib.Path(__file__).parent.absolute() / "test.msh"
        self.read_mesh(mesh_file)
        self.set_volume()

        self.lhs = []
        self.rhs = []

        # Find the boundary
        for i in range(0, self.nnodes):
            bnd = self.find_boundary(self.coords[i][:])
            if bnd < 0:
                (self.lhs).append(i)
            elif bnd > 0:
                (self.rhs).append(i)

        # Build finite element grid overlaying particles
        grid = Grid()

        self.L = []
        # bottom left
        self.X0 = [0.0, 0.0]
        self.nfem = []

        for i in range(0, self.dim):
            self.L.append(np.max(self.coords[:, i]))
            self.nfem.append(int(np.ceil(self.L[i] / self.horizon)))

        grid.build_structured_mesh(self.L, self.nfem, self.X0)

    def find_boundary(self, x):
        bnd = 0
        if x[0] < 1.5 * self.horizon:
            bnd = -1
        elif x[0] > 1.0 - 1.5 * self.horizon:
            bnd = 1
        return bnd

    def is_crack(self, x, y):
        output = 0
        p1 = x
        p2 = y
        if x[0] > y[0]:
            p2 = x
            p1 = y
        # 1e-6 makes it fall one side of central line of particles
        if p1[0] < 0.5 + 1e-6 and p2[0] > 0.5 + 1e-6:
            # draw a straight line between them
            m = (p2[1] - p1[1]) / (p2[0] - p1[0])
            c = p1[1] - m * p1[0]
            # height a x = 0.5
            height = m * 0.5 + c
            if (height > 0.5 * (1 - self.crack_length)
                    and height < 0.5 * (1 + self.crack_length)):
                output = 1
        return output


def multivar_normal(L, num_nodes):
    """
    Fn for taking a single multivar normal sample covariance matrix with
    Cholesky factor, L
    """
    zeta = np.random.normal(0, 1, size=num_nodes)
    zeta = np.transpose(zeta)

    # vector
    w_tild = np.dot(L, zeta)

    return w_tild


def noise(L, samples, num_nodes):
    """
    takes multiple samples from multivariate normal distribution with
    covariance matrix whith Cholesky factor, L
    """
    noise = []
    for i in range(samples):
        noise.append(multivar_normal(L, num_nodes))

    return np.transpose(noise)


def sim(model, steps=400, load_rate=0.00001, dt=1e-3, print_every=10):
    print("Peridynamic Simulation -- Starting")

    model.set_connectivity(0.1)
    model.set_H()

    u = []

    damage = []

    u.append(np.zeros((model.nnodes, 3)))

    damage.append(np.zeros(model.nnodes))

    verb = 1

    tim = 0.0

    # Number of nodes
    nnodes = model.nnodes

    # Start the clock
    st = time.time()

    for t in range(1, steps+1):
        tim += dt

        if verb > 0:
            print("Time step = " + str(t)
                  + ", Wall clock time for last time step= "
                  + str(time.time() - st))

        st = time.time()

        # Compute the force with displacement u[t-1]
        damage.append(np.zeros(nnodes))

        model.bond_stretch(u[t-1])
        damage[t] = model.damage()
        f = model.bond_force()

        # Simple Euler update of the solution + add the stochastic random noise
        u.append(np.zeros((nnodes, 3)))

        u[t] = u[t-1] + dt * f

        # Apply boundary conditions
        u[t][model.lhs, 1:3] = np.zeros((len(model.lhs), 2))
        u[t][model.rhs, 1:3] = np.zeros((len(model.rhs), 2))

        u[t][model.lhs, 0] = -0.5 * t * load_rate * np.ones(len(model.rhs))
        u[t][model.rhs, 0] = 0.5 * t * load_rate * np.ones(len(model.rhs))

        if verb == 1 and t % print_every == 0:
            model.write_mesh("U_"+"t"+str(t)+".vtk", damage[t], u[t])

        print('Timestep {} complete in {} s '.format(t, time.time() - st))


def main():
    """
    Stochastic peridynamics, takes multiple stable states (fully formed cracks)
    """
    st = time.time()
    model = SimpleSquare()
    sim(model, steps=10)
    print('TOTAL TIME REQUIRED {}'.format(time.time() - st))


if __name__ == "__main__":
    main()
