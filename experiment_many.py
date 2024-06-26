"""
This standard RWM script runs many simulations for different variance values 
and saves the results for plotting.
Useful to study the acceptance rate and the expected squared jump distance 
for different variance values.
"""

from interfaces import MCMCSimulation
from algorithms import *
import numpy as np
from target_distributions import *
import matplotlib.pyplot as plt
import json  # for saving values


if __name__ == "__main__":
    dim = 5    # dimension of the target and proposal distributions
    # run many simulations for different variance values
    var_value_range = np.linspace(0.000001, 2.0, 40)
    num_seeds = 3

    # save results for plotting
    acceptance_rates = []
    expected_squared_jump_distances = []

    ### keep scaling factors consistent in the target density across experiments
    ### set scaling=True for random i.i.d. scaling factors for the components
    ### choose the rough carpet or three mixture or standard multivariate normal
    # target_distribution = MultivariateNormal(dim)
    # target_distribution = RoughCarpetDistribution(dim, scaling=False)
    # target_distribution = ThreeMixtureDistribution(dim, scaling=False)
    target_distribution = Hypercube(dim, left_boundary=-1, right_boundary=1)
    # target_distribution = IIDGamma(dim, shape=2, scale=3)
    # target_distribution = IIDBeta(dim, alpha=2, beta=3)

    ### Tune other hyperparameters here
    num_iters=100000
    
    for i in range(len(var_value_range)):
        var = var_value_range[i]
        print(f"Variance {i + 1} out of {len(var_value_range)}")
        variance = (var ** 2) / (dim ** (1))
        seed_results_acceptance = []
        seed_results_esjd = []

        for seed_val in range(num_seeds):
            simulation = MCMCSimulation(dim=dim, 
                                        sigma=variance,  # 2.38**2 / dim
                                        num_iterations=num_iters,
                                        algorithm=RandomWalkMH,
                                        target_dist=target_distribution,
                                        symmetric=True,  # whether to do Metropolis or Metropolis-Hastings: symmetric proposal distribution
                                        seed=seed_val)
            
            chain = simulation.generate_samples()
            seed_results_acceptance.append(simulation.acceptance_rate())
            seed_results_esjd.append(simulation.expected_squared_jump_distance())

        # calculate average acceptance rate and ESJD for this variance value
        acceptance_rates.append(np.mean(seed_results_acceptance))
        expected_squared_jump_distances.append(np.mean(seed_results_esjd))

    print(f"Maximum ESJD: {max(expected_squared_jump_distances)}")
    print(f"Acceptance rate corresponding to maximum ESJD: {acceptance_rates[np.argmax(expected_squared_jump_distances)]}")
    print(f"Variance value corresponding to maximum ESJD: {var_value_range[np.argmax(expected_squared_jump_distances)]}")
    
    ### save the computed ESJDs, acceptance rates, and variances to a file
    data = {
        'expected_squared_jump_distances': expected_squared_jump_distances,
        'acceptance_rates': acceptance_rates,
        'var_value_range': var_value_range.tolist()
    }
    with open(f"data/{target_distribution.get_name()}_RWM_dim{dim}_{num_iters}iters.json", "w") as file:
        json.dump(data, file)

    ### plot results
    plt.plot(acceptance_rates, expected_squared_jump_distances, label='Expected squared jump distance', marker='x')   
    plt.xlabel('acceptance rate')
    plt.ylabel('ESJD')
    plt.title(f'ESJD vs acceptance rate (dim={dim})')
    filename = f"images/ESJDvsAccept_{target_distribution.get_name()}_RWM_dim{dim}_{num_iters}iters"
    plt.savefig(filename)
    plt.clf()
    # plt.show()

    plt.plot(var_value_range, acceptance_rates, label='Acceptance rate', marker='x')  # marker='o'
    plt.xlabel('Variance value (value^2 / dim)')
    plt.ylabel('Acceptance rate')
    plt.title(f'Acceptance rate for different variance values (dim={dim})')
    filename = f"images/AcceptvsVar_{target_distribution.get_name()}_RWM_dim{dim}_{num_iters}iters"
    plt.savefig(filename)
    plt.clf()
    # plt.show()

    plt.plot(var_value_range, expected_squared_jump_distances, label='Expected squared jump distance', marker='x')  # marker='o'
    plt.xlabel('Variance value (value^2 / dim)')
    plt.ylabel('ESJD')
    plt.title(f'ESJD for different variance values (dim={dim})')
    filename = f"images/ESJDvsVar_{target_distribution.get_name()}_RWM_dim{dim}_{num_iters}iters"
    plt.savefig(filename)
    plt.clf()
    # plt.show()

    ### see the last histogram to see if results are consistent
    simulation.samples_histogram(axis=0)  # plot the histogram of the first dimension
    simulation.traceplot(single_dim=True)   # single_dim=True to plot only the first dimension

