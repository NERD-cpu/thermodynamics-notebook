import numpy as np

from rachford_rice import calculate_rachford_rice


def flash_residual_function(x, T, P, eos, z):
    # Get values from unknown vector
    K   = x[:-1]  # K-values
    F_V = x[ -1]

#     if F_V < 0.0:
#         F_V = 0.0
#     if F_V > 1.0:
#         F_V = 1.0

    x_L = z / (F_V * (K - 1) + 1)
    x_V = K * x_L

    # Vapor
    f_V = eos.calculate_fugacities_with_minimum_gibbs_energy(P, T, x_V)

    # Liquid
    f_L = eos.calculate_fugacities_with_minimum_gibbs_energy(P, T, x_L)

    residual_fugacity = f_L - f_V
    residual_mass = np.sum(z * (K - 1) / (1 + F_V * (K - 1)))
    residual = np.r_[residual_fugacity, residual_mass]

    return residual


def multiphase_flash_residual_function(x, T, P, eos, z, n_extra_phases):
    shape = (n_extra_phases, z.size)

    # Get values from unknown vector
    K = x[               :-n_extra_phases].reshape(shape) # K-values
    β = x[-n_extra_phases:               ]

    denominator = 1 + (β[:, np.newaxis] * (K - 1)).sum(axis=0)
    y_iF = z / denominator
    y_i  = K * y_iF 
    print(y_i)
    # Reference phase fugacity
    f_iF = eos.calculate_fugacities_with_minimum_gibbs_energy(P, T, y_iF)

    f_i = []
    for j in range(n_extra_phases):
        f_ij = eos.calculate_fugacities_with_minimum_gibbs_energy(P, T, y_i[j])
        f_i = np.r_[f_i, f_ij]
    f_i = f_i.reshape(shape)
    
    residual_fugacity = f_iF - f_i # Broadcasting
    
    residual_mass = (z * (K - 1) / denominator).sum(axis=1)
    
    residual = np.r_[residual_fugacity.flatten(), residual_mass]
    
    print('f norm is ', np.linalg.norm(residual))
    return residual


def ss_flash(
        eos,
        P,
        T,
        z,
        K_values_initial,
        max_iter=50,
        tolerance=1.0e-3,
        print_statistics=False
):
    K = np.copy(K_values_initial)

    # Initialize error with some value
    error = 100.0

    counter = 0
    while error > tolerance and counter < max_iter:
        F_V = calculate_rachford_rice(z, K)
        x_L = z / (F_V * (K - 1) + 1)
        x_V = K * x_L

        # Vapor
        f_V = eos.calculate_fugacities_with_minimum_gibbs_energy(P, T, x_V)

        # Liquid
        f_L = eos.calculate_fugacities_with_minimum_gibbs_energy(P, T, x_L)

        f_ratio = f_L / f_V
        K *= f_ratio

        error = np.linalg.norm(f_ratio - 1)
        counter += 1

    if print_statistics:
        print('SS Flash: %d iterations, error is %g.' % (counter, error))

    return K, F_V, f_L