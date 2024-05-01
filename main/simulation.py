import numpy as np
import matplotlib.pyplot as plt
from .metropolis import MHAlgorithm
from .target import TargetDistribution
from typing import Optional, Callable
import tqdm

class MCMCSimulation:
    """Class for running a single MCMC simulation for generating samples from a target distribution 
    and visualizing the various metrics and results."""
    def __init__(self, 
                 dim: int, 
                 sigma: float, 
                 num_iterations: int = 1000, 
                 algorithm: MHAlgorithm = None,
                 target_dist: TargetDistribution = None,
                 symmetric: bool = True,
                 seed: Optional[int] = None,
                 beta_ladder: Optional[list] = None,
                 swap_acceptance_rate: Optional[float] = None,):
        self.num_iterations = num_iterations
        self.target_dist = target_dist
        self.algorithm = algorithm(dim, 
                                   sigma, 
                                   target_dist, 
                                   symmetric, 
                                   beta_ladder=beta_ladder, 
                                   swap_acceptance_rate=swap_acceptance_rate)   # comment out last two lines for standard rwm
        if seed:
            np.random.seed(seed)

    
    def reset(self):
        """Reset the simulation to the initial state."""
        self.algorithm.reset()

    def has_run(self):
        """Return whether the algorithm has been run."""
        return len(self.algorithm.chain) > 1

    def generate_samples(self):
        if self.has_run():
            raise ValueError("Please reset the algorithm before running it again.")
        
        print("Running the MCMC simulation...")
        with tqdm.tqdm(total=self.num_iterations, desc="Running MCMC", unit="iteration") as pbar:
            for i in range(self.num_iterations):
                self.algorithm.step()
                pbar.update(1)

        return self.algorithm.chain
    
    def acceptance_rate(self):
        """Return the acceptance rate of the algorithm."""
        if not self.has_run():
            raise ValueError("The algorithm has not been run yet.")
        return self.algorithm.acceptance_rate

    def expected_squared_jump_distance(self):
        """Calculate the expected squared jump distance for the 
        Markov chain. 
        Returns:
            float: The expected squared jump distance.
        """
        if not self.has_run():
            raise ValueError("The algorithm has not been run yet.")
        chain = np.array(self.algorithm.chain)
        squared_jumps = np.sum((chain[1:] - chain[:-1]) ** 2, axis=1)
        return np.mean(squared_jumps)

    def traceplot(self, single_dim=False):
        """Visualize the traceplot of the Markov chain.
        The traceplot plots the values of the parameters 
        against the iteration number in the Markov chain.
        """
        if not self.has_run():
            raise ValueError("The algorithm has not been run yet.")
        
        chain = np.array(self.algorithm.chain)
        if single_dim:
            plt.plot(chain[:, 0], label=f"Dimension 1", alpha=0.7, lw=0.5)
        else:
            for i in range(self.algorithm.dim):
                plt.plot(chain[:, i], label=f"Dimension {i + 1}", alpha=0.7, lw=0.5)

        plt.xlabel('Iteration')
        plt.ylabel('Value')
        plt.legend()
        plt.title(f'variance = {self.algorithm.var:.3f}, acceptance rate = {self.acceptance_rate():.3f}, ESJD = {self.expected_squared_jump_distance():.3f}')
        plt.show()

    def autocorrelation_plot(self):
        """Visualize the autocorrelation of the Markov chain.
        """
        if not self.has_run():
            raise ValueError("The algorithm has not been run yet.")
        chain = np.array(self.algorithm.chain)
        autocorr = np.zeros(self.algorithm.dim)
        for i in range(self.algorithm.dim):
            autocorr[i] = np.correlate(chain[:, i] - np.mean(chain[:, i]), chain[:, i] - np.mean(chain[:, i]), mode='full')[chain.shape[0] - 1]
        
        plt.stem(range(len(autocorr)), autocorr)
        plt.xlabel('Lag')
        plt.ylabel('Autocorrelation')
        plt.show()

    def samples_histogram(self, num_bins=50, dim=0):
        """Plot a histogram of the samples overlaid with the target density for the first
        coordinate. Use to ensure the correctness of samples (convergence of chain).
        This assumes that the target density can be divided into components.

        Args:
            samples (ndarray): The samples generated by the Markov chain.
            num_bins (int): The number of bins in the histogram. Default is 50.
            dim (int): The dimension of the samples to plot. Default is 0 (first component)
        """
        # Generate histogram of samples
        samples = np.array(self.algorithm.chain)[:, dim]

        plt.hist(samples, bins=num_bins, density=True, alpha=0.5, label='Samples')

        # Generate values for plotting the target density
        x = np.array([np.array([v]) for v in np.linspace(min(-20, min(samples) - 5), max(20, max(samples) + 5), 1000)])

        ## For plotting the target density (red dashed line)
        # y = np.zeros_like(x)
        # for i in range(len(x)):
        #     y[i] = self.target_dist.density(x[i])   # how to visualize a single component of the target density?

        # plt.plot(x, y, color='red', linestyle='--', linewidth=2, label='Target Density')
        plt.xlabel('Value')
        plt.ylabel('Density')
        plt.legend()
        plt.title(f'var = {self.algorithm.var:.3f}, a = {self.acceptance_rate():.3f}, ESJD = {self.expected_squared_jump_distance():.3f}, num_iter = {self.num_iterations}')
        plt.show()