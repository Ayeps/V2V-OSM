import os

import matplotlib.pyplot as plt
import numpy as np

import vtovosm as vtv
import logging

# Config
plt.rcParams["figure.figsize"] = (8, 5)
densities = [10, 20, 30, 40, 50, 60, 70, 80, 120, 160]

count_veh = 337  # from results_all.keys() = [48, 96, 145, 193, 241, 289, 337, 386, 578, 771]
count_veh_neubau = 112  # from results_neubau.keys() = [16, 32, 48, 64, 80, 96, 112, 129, 193, 257]
dir_out = os.path.join('images', 'viriyasitavat_comparison')
overwrite = False

# Setup
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

logging.info('Loading files')
os.makedirs(dir_out, exist_ok=True)
results_all = vtv.utils.load('results/viriyasitavat_comparison/result_analysis.pickle.xz')
results_unif = vtv.utils.load('results/viriyasitavat_comparison_uniform/result_analysis.pickle.xz')
results_neubau = vtv.utils.load('results/viriyasitavat_comparison_neubau/result_analysis.pickle.xz')

# Plot average network connectivites vs. vehicle densities
filename = 'net_con_vs_veh_dens.pdf'
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    mean_net_connectivities = np.array(
        [(density, np.mean(result['net_connectivities'])) for density, result in sorted(results_all.items())])
    mean_net_connectivities_neubau = np.array(
        [(density, np.mean(result['net_connectivities'])) for density, result in sorted(results_neubau.items())])
    mean_net_connectivities_unif = np.array(
        [(density, np.mean(result['net_connectivities'])) for density, result in sorted(results_unif.items())])
    mean_net_connectivities_paper = np.array([12.67, 18.92, 21.33, 34.75, 69.72, 90.05, 97.46, 98.97, 99.84, 100]) / 100

    plt.figure()
    plt.plot(densities, mean_net_connectivities[:, 1], label='Upper West Side, New York City - SUMO')
    plt.plot(densities, mean_net_connectivities_neubau[:, 1], label='Neubau, Vienna - SUMO')
    plt.plot(densities, mean_net_connectivities_unif[:, 1], label='Upper West Side - uniform distribution')
    plt.plot(densities, mean_net_connectivities_paper, label='Manhattan grid (Viriyasitavat et al.)')
    plt.grid(True)
    plt.xlabel(r'Vehicle density $[1/km^2]$')
    plt.ylabel('Relative size of largest cluster')
    plt.title('Network Connectivity')
    plt.legend()
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# Plot link duration pmf for one specific vehicle density
filename = 'link_dur_pmf_unweighted.pdf'
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    link_durations = results_all[count_veh]['link_durations']
    link_durations_neubau = results_neubau[count_veh_neubau]['link_durations'].durations_con
    bins = int(max(link_durations) - min(link_durations))

    plt.figure()
    hist = plt.hist(link_durations, bins=bins, normed=True, alpha=0.6, label='Upper West Side, New York City')
    bins_neubau = int(max(link_durations_neubau) - min(link_durations_neubau))
    hist_neubau = plt.hist(link_durations_neubau, bins=bins_neubau, normed=True, alpha=0.6, label='Neubau, Vienna')
    plt.xlim((0, 100))
    plt.grid(True)
    plt.xlabel('Link duration [s]')
    plt.ylabel('Probability')
    plt.title('Link Duration Distribution')
    plt.legend()
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# Plot weighted link duration (1) pmf for one specific vehicle density
filename = 'link_dur_pmf_weighted_1.pdf'
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    plt.figure()
    hist = plt.hist(link_durations, bins=bins, normed=True, weights=link_durations, alpha=0.6,
                    label='Upper West Side, New York City')
    hist_neubau = plt.hist(link_durations_neubau, bins=bins_neubau, normed=True, weights=link_durations_neubau, alpha=0.6,
                           label='Neubau, Vienna')
    plt.xlim((0, 100))
    plt.grid(True)
    plt.xlabel('Link duration [s]')
    plt.ylabel('Probability')
    plt.title('Link Duration Distribution - Weighted 1')
    plt.legend()
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# Plot weighted link duration (2) pmf for one specific vehicle density
filename = 'link_dur_pmf_weighted_2.pdf'
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    link_durations_w = np.zeros(sum(link_durations))
    idx = 0
    for duration in link_durations:
        link_durations_w[idx:idx + duration] = 1 + np.arange(duration)
        idx += duration

    link_durations_w_neubau = np.zeros(sum(link_durations_neubau))
    idx = 0
    for duration in link_durations_neubau:
        link_durations_w_neubau[idx:idx + duration] = 1 + np.arange(duration)
        idx += duration

    bins = int(max(link_durations_w) - min(link_durations_w))

    plt.figure()
    hist = plt.hist(link_durations_w, bins=bins, normed=True, alpha=0.6, label='Upper West Side, New York City')
    bins_neubau = int(max(link_durations_w_neubau) - min(link_durations_w_neubau))
    hist = plt.hist(link_durations_w_neubau, bins=bins_neubau, normed=True, alpha=0.6, label='Neubau, Vienna')
    plt.xlim((0, 100))
    plt.grid(True)
    plt.xlabel('Link duration [s]')
    plt.ylabel('Probability')
    plt.title('Link Duration Distribution - Weighted 2')
    plt.legend()
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# Plot average link durations (weighted and unweighted) vs. vehicle densities
filename = 'link_dur_vs_veh_dens.pdf'
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    mean_link_durations = np.array(
        [(density, np.mean(result['link_durations'])) for density, result in sorted(results_all.items())])
    mean_link_durations_neubau = np.array(
        [(density, np.mean(result['link_durations'].durations_con)) for density, result in sorted(results_neubau.items())])

    mean_link_durations_w = np.zeros([len(results_all), 2])
    for idx, (density, result) in enumerate(sorted(results_all.items())):
        link_durations = result['link_durations']
        link_durations_w = np.zeros(sum(link_durations))
        idx_w = 0
        for duration in link_durations:
            link_durations_w[idx_w:idx_w + duration] = 1 + np.arange(duration)
            idx_w += duration
        mean_link_durations_w[idx, :] = (density, np.mean(mean_link_durations_w))

    plt.figure()
    plt.plot(densities, mean_link_durations[:, 1], label='Upper West Side, New York City - Unweighted')
    plt.plot(densities, mean_link_durations_w[:, 1], label='Upper West Side, New York City - Weighted 1')
    plt.plot(densities, mean_link_durations_neubau[:, 1], label='Neubau, Vienna - Austria')
    plt.grid(True)
    plt.xlabel(r'Vehicle density $[1/km^2]$')
    plt.ylabel('Average link duration (s)')
    plt.title('Link Duration')
    plt.legend()
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# Plot average number of connection periods vs. vehicle densities
filename = 'con_per_vs_veh_dens.pdf'
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    mean_con_periods = np.array(
        [(density, result['connection_periods_mean']) for density, result in sorted(results_all.items())])
    mean_con_periods_neubau = np.array(
        [(density, result['connection_periods_mean']) for density, result in sorted(results_neubau.items())])

    plt.figure()
    plt.plot(densities, mean_con_periods[:, 1], label='Upper West Side, New York City')
    plt.plot(densities, mean_con_periods_neubau[:, 1], label='Neubau, Vienna')
    plt.grid(True)
    plt.xlabel(r'Vehicle density $[1/km^2]$')
    plt.ylabel('Average number of connection periods per vehicle pair')
    plt.title('Connection Periods')
    plt.legend()
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# Plot average connection durations vs. vehicle densities
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    mean_con_durations = np.array(
        [(density, result['connection_duration_mean']) for density, result in sorted(results_all.items())])
    mean_con_durations_neubau = np.array(
        [(density, result['connection_duration_mean']) for density, result in sorted(results_neubau.items())])

    plt.figure()
    plt.plot(densities, mean_con_durations[:, 1], label='Upper West Side, New York City')
    plt.plot(densities, mean_con_durations_neubau[:, 1], label='Neubau, Vienna')
    plt.grid(True)
    plt.xlabel(r'Vehicle density $[1/km^2]$')
    plt.ylabel('Average connection duration [s]')
    plt.title('Connection Duration')
    plt.legend()
    filename = 'con_dur_vs_veh_dens.pdf'
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# Plot average rehealing time vs. vehicle densities
filename = 'reheal_time_vs_veh_dens.pdf'
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    mean_rehaling_times = np.array(
        [(density, np.mean(result['rehealing_times'])) for density, result in sorted(results_all.items())])
    mean_rehaling_times_neubau = np.array(
        [(density, np.mean(result['rehealing_times'])) for density, result in sorted(results_neubau.items())])

    plt.figure()
    plt.plot(densities, mean_rehaling_times[:, 1], label='Upper West Side, New York City')
    plt.plot(densities, mean_rehaling_times_neubau[:, 1], label='Neubau - Vienna')
    plt.grid(True)
    plt.xlabel(r'Vehicle density $[1/km^2]$')
    plt.ylabel('Average rehealing time [s]')
    plt.title('Reahaling Time')
    plt.legend()
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# Plot connection duration pmf for ones specific vehicle density
filename = 'con_dur_pmf_unweighted.pdf'
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    con_durations = results_all[count_veh]['connection_durations']
    con_durations_neubau = results_neubau[count_veh_neubau]['connection_durations']
    bins = int(max(con_durations) - min(con_durations))

    plt.figure()
    hist = plt.hist(con_durations, bins=bins, normed=True, alpha=0.6, label='Upper West Side, New York City')
    bins_neubau = int(max(con_durations_neubau) - min(con_durations_neubau))
    hist_neubau = plt.hist(con_durations_neubau, bins=bins_neubau, normed=True, alpha=0.6, label='Neubau - Vienna')
    plt.xlim((0, 100))
    plt.grid(True)
    plt.xlabel('Connection duration [s]')
    plt.ylabel('Probability')
    plt.title('Connection Duration Distribution')
    plt.legend()
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# Plot weighted (1) connection duration pmf for ones specific vehicle density
filename = 'con_dur_pmf_weighted_1.pdf'
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    plt.figure()
    hist = plt.hist(con_durations, bins=bins, normed=True, weights=con_durations, alpha=0.6,
                    label='Upper West Side, New York City')
    hist_neubau = plt.hist(con_durations_neubau, bins=bins_neubau, normed=True, weights=con_durations_neubau, alpha=0.6,
                           label='Neubau, Vienna')
    plt.xlim((0, 300))
    plt.grid(True)
    plt.xlabel('Connection duration [s]')
    plt.ylabel('Probability')
    plt.title('Connection Duration Distribution - Weighted 1')
    plt.legend()
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# Plot weighted (2) connection duration pmf for ones specific vehicle density
filename = 'con_dur_pmf_weighted_2.pdf'
path_out = os.path.join(dir_out, filename)

if os.path.isfile(path_out) and not overwrite:
    logging.warning('file {} already exists. Skipping'.format(filename))
else:
    con_durations_w = np.zeros(sum(con_durations))
    idx = 0
    for duration in con_durations:
        con_durations_w[idx:idx + duration] = 1 + np.arange(duration)
        idx += duration

    con_durations_w_neubau = np.zeros(sum(con_durations_neubau))
    idx = 0
    for duration in con_durations_neubau:
        con_durations_w_neubau[idx:idx + duration] = 1 + np.arange(duration)
        idx += duration

    bins = int(max(con_durations_w) - min(con_durations_w))

    plt.figure()
    hist = plt.hist(con_durations_w, bins=bins, normed=True, alpha=0.6, label='Upper West Side, New York City')
    bins_neubau = int(max(con_durations_w_neubau) - min(con_durations_w_neubau))
    hist_neubau = plt.hist(con_durations_w_neubau, bins=bins_neubau, normed=True, alpha=0.6, label='Neubau, Vienna')
    plt.xlim((0, 300))
    plt.grid(True)
    plt.xlabel('Connection duration [s]')
    plt.ylabel('Probability')
    plt.title('Connection Duration Distribution - Weighted 2')
    plt.legend()
    plt.savefig(path_out)
    logging.info('Saved {}'.format(filename))

# TODO: plot results of building tolerance analysis