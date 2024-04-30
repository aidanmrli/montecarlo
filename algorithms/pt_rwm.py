import numpy as np
from scipy.stats import multivariate_normal as normal
from main import MHAlgorithm
from typing import Callable

class ParallelTemperingRWM(MHAlgorithm):
    """Implementation of the Random Walk Metropolis-Hastings with Parallel Tempering algorithm for sampling from a target distribution."""
    def __init__(
            self, 
            dim, 
            var, 
            target_dist: Callable = None, 
            symmetric=True,
            temp_ladder=None,
            geom_temp_spacing=False,
            ):
        super().__init__(dim, var, target_dist, symmetric)
        self.num_swap_attempts = 0
        self.num_acceptances = 0    # use this to calculate acceptance rate
        self.acceptance_rate = 0    # this refers to SWAP acceptance rate
        self.chains = []
        self.temp_ladder = None
        # [1, 0.70529181, 0.49111924, 0.3433667, 0.23914574, 0.16521939, 0.11696551, 0.08199772, 0.05699343, 0.01]
        if self.temp_ladder is not None:
            for i in range(len(self.temp_ladder)):  # only if the temp ladder is not none
                self.chains.append(self.chain.copy())

        else:
            self.temp_ladder = []
            if geom_temp_spacing:
                # construct a geometrically spaced temperature ladder
                beta_0, beta_min = 1, 1e-2
                curr_beta = beta_0
                c = 0.5     # set the geometric spacing constant
                while curr_beta > beta_min:
                    self.temp_ladder.append(curr_beta)
                    self.chains.append(self.chain.copy())  # initialize one chain for each temperature
                    curr_beta = curr_beta * c
                
                self.temp_ladder.append(beta_min)
                self.chains.append(self.chain.copy())

                # iteratively construct the inverse temperatures using simulation-based approach
            else:
                # TODO: implement the simulation-based approach to construct spacing of prob 0.23
                # also consider adaptive temperature ladder
                self.construct_temp_ladder_iteratively()
                    
        self.chain = self.chains[0]  # the first chain is the "cold" chain


    def construct_temp_ladder_iteratively(self):
        """Construct the temperature ladder iteratively using a simulation-based approach."""
        beta_0, beta_min = 1, 1e-2
        curr_beta = beta_0

        while curr_beta > beta_min:
            self.temp_ladder.append(curr_beta)
            self.chains.append(self.chain.copy())  # initialize one chain for each temperature

            # Find the next inverse temperature beta
            rho_n = 0
            new_beta = curr_beta / (1 + np.exp(rho_n))
            num_iters = 0

            while new_beta > beta_min:
                num_iters += 1
                curr_beta_chain = self.chain.copy()
                new_beta_chain = self.chain.copy()
                chains = [(curr_beta_chain, curr_beta), (new_beta_chain, new_beta)]

                # get an average swap probability between the two chains by drawing 100 samples
                # and calculating the swap probability for each sample

                # draw samples from each of the target distributions of the curr_beta and new_beta chains
                burn_in = 0
                total_iterations = 100
                total_samples = total_iterations - burn_in
                for chain, beta in chains:
                    for _ in range(total_iterations):
                        means = [np.zeros(self.dim), np.zeros(self.dim), np.zeros(self.dim)]
                        means[:][0], means[:][0] = -5, 5

                        covs = [np.eye(50) / np.sqrt(self.dim), np.eye(50) / np.sqrt(self.dim), np.eye(50) / np.sqrt(self.dim)]

                        random_integer = np.random.randint(0, 3, size=50)  # randomly choose a mode from 0 to 2 inclusive
                        target_mean, target_cov = means[random_integer], covs[random_integer]
                        proposed_state = np.random.multivariate_normal(target_mean, target_cov / beta)
                        
                        chain.append(proposed_state)
                
                # then calculate the swap probability between these chains for each sample
                # and average them to get an average swap probability
                avg_swap_prob = np.zeros(total_samples)
                for i in range(total_samples):
                    log_swap_prob = (
                        curr_beta * np.log(self.target_dist(new_beta_chain[burn_in + 1 + i])) + 
                        new_beta * np.log(self.target_dist(curr_beta_chain[burn_in + 1 + i])) -
                        curr_beta * np.log(self.target_dist(curr_beta_chain[burn_in + 1 + i])) -
                        new_beta * np.log(self.target_dist(new_beta_chain[burn_in + 1 + i]))
                        )
                    swap_prob = min(1, np.exp(log_swap_prob))
                    # print("swap_prob:", swap_prob)
                    avg_swap_prob[i] = swap_prob
                # print("Average swap probability: ", avg_swap_prob, "new_beta: ", new_beta)

                avg_swap_prob = np.mean(avg_swap_prob)

                # if the average swap probability is close to 0.234
                # also consider experimenting 
                error = 0.01
                if abs(0.234 - avg_swap_prob) <= error: 
                    curr_beta = new_beta
                    print("new beta added to inverse temperature ladder: ", curr_beta, 
                          "\nSwap probability: ", avg_swap_prob)
                    break
                else:   # use the recurrence defined in the paper
                    print("Average swap probability: ", avg_swap_prob, "new_beta: ", new_beta)
                    rho_n = rho_n + (avg_swap_prob - 0.234) / np.sqrt(num_iters)
                    new_beta = curr_beta / (1 + np.exp(rho_n))

            if curr_beta <= beta_min or new_beta <= beta_min:
                break

        self.temp_ladder.append(beta_min)
        self.chains.append(self.chain.copy())
        print("Finished constructing the temperature ladder.")
        print("Inverse temperature ladder: ", self.temp_ladder)

    def attempt_swap(self, j, k):
        """Attempt to swap states between two chains based on Metropolis criteria."""
        swap_prob = min(1, np.exp(self.log_swap_prob(j, k)))
        self.num_swap_attempts += 1
        if np.random.random() < swap_prob:
            # swap the states
            temp = self.chains[k][-1].copy()
            self.chains[k][-1] = self.chains[j][-1].copy()
            self.chains[j][-1] = temp
            self.num_acceptances += 1   # increment the number of SWAP acceptances
            self.acceptance_rate = self.num_acceptances / self.num_swap_attempts


    def log_swap_prob(self, j, k):
        """Calculate the log probability of swapping states between two chains."""
        log_prob = (
            self.temp_ladder[j] * np.log(self.target_dist(self.chains[k][-1])) + 
            self.temp_ladder[k] * np.log(self.target_dist(self.chains[j][-1])) -
            self.temp_ladder[j] * np.log(self.target_dist(self.chains[j][-1])) -
            self.temp_ladder[k] * np.log(self.target_dist(self.chains[k][-1]))
                )
        return log_prob
    
    def step(self, swap=False):
        """Take a step using the Random Walk Metropolis-Hastings algorithm.
        Add the new state to the chain with probability min(1, A) where A is the acceptance probability.
        """
        for i in range(len(self.chains)):
            curr_chain = self.chains[i]
            if swap and i < len(self.chains) - 1:
                self.attempt_swap(i, i+1)   # this handles swap acceptance rate as well
            else:
                # 2.38**2 / (dim * beta)
                proposed_state = np.random.multivariate_normal(curr_chain[-1], np.eye(self.dim) * (self.var / self.temp_ladder[i]))
                log_accept_ratio = self.log_accept_prob(proposed_state, curr_chain[-1], self.temp_ladder[i])

                # accept the proposed state with probability min(1, A)
                if log_accept_ratio > 0 or np.random.random() < np.exp(log_accept_ratio):
                    curr_chain.append(proposed_state)
                else:
                    curr_chain.append(curr_chain[-1])


    def log_accept_prob(self, proposed_state, current_state, beta):
        """Calculate the log acceptance probability for the proposed state given the current state.
        We use the log density of the target distribution for numerical stability in high dimensions.

        Args:
            proposed_state (np.ndarray): The proposed state.
            current_state (np.ndarray): The current state.
            symmetric (bool): Whether the proposal distribution is symmetric. Default is False.
            
        Returns:
            float: The log acceptance probability."""
        if self.symmetric:
            return beta * (np.log(self.target_dist(proposed_state)) - np.log(self.target_dist(current_state)))
        else:
            log_target_term = np.log(self.target_dist(proposed_state)) - np.log(self.target_dist(current_state))
            log_proposal_term = (np.log(normal.pdf(current_state, mean=proposed_state, 
                                                   cov=np.eye(self.dim) * (self.var))) 
                                - np.log(normal.pdf(proposed_state, mean=current_state, 
                                                    cov=np.eye(self.dim) * (self.var))))

            return (log_target_term + log_proposal_term) * beta
