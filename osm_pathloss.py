""" Generates streets, buildings and vehicles from OpenStreetMap data with osmnx"""

# Standard imports
import time
import argparse
import os.path
import pickle
# Extension imports
import numpy as np
import osmnx_git as ox # TODO: update osmnx and delete _git
import matplotlib.pyplot as plt
import ipdb
import networkx as nx
import shapely.geometry as geom
import shapely.ops as ops
# Local imports
import pathloss

def plot_streets_and_buildings(streets, buildings=None, show=True, filename=None, dpi=300):
    """ Plots streets and buildings"""

    # TODO: street width!
    # TODO: bug when plotting buildings, inner area not empty!
    fig, axi = ox.plot_graph(
        streets, show=False, close=False, node_size=0, dpi=dpi, edge_color='#333333')

    if buildings is not None:
        ox.plot_buildings(buildings, fig=fig, ax=axi,
                          show=False, close=False, dpi=dpi, color='#999999')

    if show:
        plt.show()

    if filename is not None:
        plt.savefig(filename)
        plt.close()

    return fig, axi


def download_place(place, network_type='drive', file_prefix=None, which_result=1, project=True):
    """ Downloads streets and buildings for a place, saves the data to disk and returns them """

    if file_prefix is None:
        file_prefix = 'data/{}'.format(string_to_filename(place))

    # Streets
    streets = ox.graph_from_place(
        place, network_type=network_type, which_result=which_result)
    if project:
        streets = ox.project_graph(streets)
    filename_streets = '{}_streets.pickle'.format(file_prefix)
    pickle.dump(streets, open(filename_streets, 'wb'))

    # Buildings
    gdf = ox.gdf_from_place(place, which_result=which_result)
    polygon = gdf['geometry'].iloc[0]
    buildings = ox.create_buildings_gdf(polygon)
    if project:
        buildings = ox.project_gdf(buildings)
    filename_buildings = '{}_buildings.pickle'.format(file_prefix)
    pickle.dump(buildings, open(filename_buildings, 'wb'))

    # Return data
    data = {'streets': streets, 'buildings': buildings}
    return data


def load_place(file_prefix):
    """ Loads previously downloaded street and building data of a place"""

    filename_buildings = '{}_buildings.pickle'.format(file_prefix)
    buildings = pickle.load(open(filename_buildings, 'rb'))
    filename_streets = '{}_streets.pickle'.format(file_prefix)
    streets = pickle.load(open(filename_streets, 'rb'))
    place = {'streets': streets, 'buildings': buildings}
    return place


def string_to_filename(string):
    """ Cleans a string up to be used as a filename"""
    keepcharacters = ('_', '-')
    filename = ''.join(c for c in string if c.isalnum()
                       or c in keepcharacters).rstrip()
    filename = filename.lower()
    return filename


def setup(debug=False):
    """ Sets osmnx up"""
    if debug:
        ox.config(log_console=True, use_cache=True)
    else:
        ox.config(log_console=False, use_cache=False)

def add_geometry(streets):
    """ Adds geometry object to the edges of the graph where they are missing"""
    for u_node, v_node, data in streets.edges(data=True):
        if 'geometry' not in data:
            coord_x1 = streets.node[u_node]['x']
            coord_y1 = streets.node[u_node]['y']
            coord_x2 = streets.node[v_node]['x']
            coord_y2 = streets.node[v_node]['y']
            data['geometry'] = geom.LineString(
                [(coord_x1, coord_y1), (coord_x2, coord_y2)])


def check_geometry(streets):
    """ Checks if all edges of the graph have a geometry object"""
    complete = True
    for _, _, data in streets.edges(data=True):
        if 'geometry' not in data:
            complete = False
            break

    return complete


def line_intersects_buildings(line, buildings):
    """ Checks if a line intersects with any of the buildings"""
    # TODO: check if it's faster to convert sequence of polygons into a multipolygon and use it

    intersects = False
    for geometry in buildings['geometry']:
        if line.intersects(geometry):
            intersects = True
            break

    return intersects


def line_intersects_points(line, points, margin=1):
    """ Checks if a line intersects with any of the points within a margin """

    intersects = False

    for point in points:
        proj = line.project(point)
        point_in_roi = (proj > 0) and (proj < line.length)
        distance_small = line.distance(point) < margin
        if point_in_roi and distance_small:
            intersects = True
            break

    return intersects


def veh_cons_are_nlos(point_own, point_vehs, buildings):
    """ Determines for each connection if it is NLOS or not"""

    is_nlos = np.zeros(np.size(point_vehs), dtype=bool)

    for index, point in np.ndenumerate(point_vehs):
        line = geom.LineString([point_own, point])
        is_nlos[index] = line_intersects_buildings(line, buildings)

    return is_nlos

def veh_cons_are_olos(point_own, point_vehs, margin=1):
    """ Determines for each LOS/OLOS connection if it is OLOS """

    # TODO: Also use NLOS vehicles!
    # TODO: working properly? still too many LOS vehicles?

    is_olos = np.zeros(np.size(point_vehs), dtype=bool)

    for index, point in np.ndenumerate(point_vehs):
        line = geom.LineString([point_own, point])
        indices_other = np.ones(np.size(point_vehs), dtype=bool)
        indices_other[index] = False
        is_olos[index] = line_intersects_points(line, point_vehs[indices_other], margin=margin)

    return is_olos


def get_street_lengths(streets):
    """ Returns the lengths of the streets in a graph"""

    # NOTE: The are small differences in the values of data['geometry'].length
    # and data['length']
    lengths = np.zeros(streets.number_of_edges())
    for index, street in enumerate(streets.edges_iter(data=True)):
        lengths[index] = street[2]['length']
    return lengths


def choose_random_streets(lengths, count=1):
    """ Chooses random streets with probabilities relative to their length"""
    total_length = sum(lengths)
    probs = lengths / total_length
    count_streets = np.size(lengths)
    indices = np.zeros(count, dtype=int)
    indices = np.random.choice(count_streets, size=count, p=probs)
    return indices


def choose_random_point(street, count=1):
    """Chooses random points along street """
    distances = np.random.random(count)
    points = np.zeros_like(distances, dtype=object)
    for index, dist in np.ndenumerate(distances):
        points[index] = street.interpolate(dist, normalized=True)

    return points


def extract_point_array(points):
    """Extracts coordinates form a point array """
    coords_x = np.zeros(np.size(points), dtype=float)
    coords_y = np.zeros(np.size(points), dtype=float)

    for index, point in np.ndenumerate(points):
        coords_x[index] = point.x
        coords_y[index] = point.y

    return coords_x, coords_y


def find_center_veh(coords_x, coords_y):
    """Finds the index of the vehicle at the center of the map """
    min_x = np.amin(coords_x)
    max_x = np.amax(coords_x)
    min_y = np.amin(coords_y)
    max_y = np.amax(coords_y)
    mean_x = (min_x + max_x) / 2
    mean_y = (min_y + max_y) / 2
    coords_center = np.array((mean_x, mean_y))
    coords_veh = np.vstack((coords_x, coords_y)).T
    distances_center = np.linalg.norm(
        coords_center - coords_veh, ord=2, axis=1)
    index_center_veh = np.argmin(distances_center)
    return index_center_veh

def line_route_between_nodes(node_from, node_to, graph):
    """Determines the line representing the shortest path between two nodes"""

    route = nx.shortest_path(graph, node_from, node_to, weight='length')
    edge_nodes = list(zip(route[:-1], route[1:]))
    lines = []
    for u_node, v_node in edge_nodes:
        # If there are parallel edges, select the shortest in length
        data = min([data for data in graph.edge[u_node][v_node].values()], \
                   key=lambda x: x['length'])
        lines.append(data['geometry'])

    line = ops.linemerge(lines)
    return line

def check_if_cons_orthogonal(streets_wave, graph_veh_own, graphs_veh_other, max_angle=np.pi):
    """Determines if the condition is NLOS on an orthogonal street for every possible connection to
    one node """
    node_own = graph_veh_own.graph['node_veh']
    streets_wave_local = nx.compose(graph_veh_own, streets_wave)
    count_veh_other = np.size(graphs_veh_other)

    is_orthogonal = np.zeros(count_veh_other, dtype=bool)
    coords_max_angle = np.zeros((count_veh_other, 2))
    for index, graph in enumerate(graphs_veh_other):

        node_v = graph.graph['node_veh']
        streets_wave_local_iter = nx.compose(graph, streets_wave_local)

        # TODO: Use angles as weight and not length?
        route = line_route_between_nodes(node_own, node_v, streets_wave_local_iter)
        angles = angles_along_line(route)
        angles_wrapped = np.pi - np.abs(wrap_to_pi(angles))

        sum_angles = sum(angles_wrapped)
        if sum_angles < max_angle:
            is_orthogonal[index] = True
        else:
            is_orthogonal[index] = False

        # Determine position of max angle
        index_angle = np.argmax(angles_wrapped)
        route_coords = np.array(route.xy)
        coords_max_angle[index, :] = route_coords[:, index_angle+1]

    return is_orthogonal, coords_max_angle


def split_line_at_point(line, point):
    """Splits a line at the point on the line """
    if line.distance(point) > 1e-8:
        raise ValueError('Point not on line')

    # NOTE: Use small circle instead of point to get around floating point precision
    circle = point.buffer(1e-8)
    line_split = ops.split(line, circle)
    line_before = line_split[0]
    line_after = line_split[2]

    return line_before, line_after


def angles_along_line(line):
    """Determines the the angles along a line"""

    coord_prev = []
    coords = line.coords
    angles = np.zeros(len(coords) - 2)
    angle_temp_prev = 0

    for index, coord in enumerate(coords[1:]):
        coord_prev = coords[index]
        angle_temp = np.arctan2(coord[0] - coord_prev[0], coord[1] - coord_prev[1])
        if index != 0:
            if angle_temp - angle_temp_prev < np.pi:
                angles[index-1] = angle_temp - angle_temp_prev + np.pi
            else:
                angles[index-1] = angle_temp - angle_temp_prev - np.pi
        angle_temp_prev = angle_temp

    return angles

def wrap_to_pi(angle):
    """ Limits angle from -pi to +pi"""
    return (angle + np.pi) % (2*np.pi) - np.pi


def add_edges_if_los(graph, buildings, max_distance=50):
    """Adds edges to the streets graph if there is none between 2 nodes if there is none, the have
    no buildings in between and are only a certain distance apart"""

    for index, node_u in enumerate(graph.nodes()):
        coords_u = np.array((graph.node[node_u]['x'], graph.node[node_u]['y']))
        for node_v in graph.nodes()[index + 1:]:

            # Check if nodes are already connected
            if graph.has_edge(node_u, node_v):
                continue
            coords_v = np.array(
                (graph.node[node_v]['x'], graph.node[node_v]['y']))
            distance = np.linalg.norm(coords_u - coords_v, ord=2)

            # Check if the nodes are further apart than the max distance
            if distance > max_distance:
                continue

            # Check if there are buildings between the nodes
            line = geom.asLineString(
                ((coords_u[0], coords_u[1]), (coords_v[0], coords_v[1])))
            if line_intersects_buildings(line, buildings):
                continue

            # Add edge between nodes
            edge_attr = {'length': distance, 'geometry': line}
            graph.add_edge(node_u, node_v, attr_dict=edge_attr)

def print_nnl(text):
    """Print without adding a new line """
    print(text, end='', flush=True)

def main_test(place, which_result=1, count_veh=100, max_pl=100, debug=False):
    """ Test the whole functionality"""

    # Setup
    setup(debug)
    if debug:
        print('RUNNING MAIN SIMULATION')

    # Load data
    if debug:
        time_start = time.process_time()
        time_start_tot = time_start
        print_nnl('Loading data')
    file_prefix = 'data/{}'.format(string_to_filename(place))
    filename_data_streets = 'data/{}_streets.pickle'.format(
        string_to_filename(place))
    filename_data_buildings = 'data/{}_buildings.pickle'.format(
        string_to_filename(place))

    if os.path.isfile(filename_data_streets) and os.path.isfile(filename_data_buildings):
        # Load from file
        if debug:
            print_nnl('from disk:')
        data = load_place(file_prefix)
    else:
        # Load from internet
        if debug:
            print_nnl('from the internet:')
        data = download_place(place, which_result=which_result)

    if debug:
        time_diff = time.process_time() - time_start
        print_nnl(' {:.3f} seconds\n'.format(time_diff))

    # Plot streets and buildings
    plot_streets_and_buildings(data['streets'], data['buildings'], show=False, dpi=300)

    # Choose random streets and position on streets
    if debug:
        time_start = time.process_time()
        print_nnl('Building graph for wave propagation:')
    streets = data['streets']
    buildings = data['buildings']
    # Vehicles are placed in a undirected version of the graph because electromagnetic
    # waves do not respect driving directions
    add_geometry(streets)
    streets_wave = streets.to_undirected()
    add_edges_if_los(streets_wave, buildings)
    if debug:
        time_diff = time.process_time() - time_start
        print_nnl(' {:.3f} seconds\n'.format(time_diff))

    if debug:
        time_start = time.process_time()
        print_nnl('Choosing random vehicle positions:')
    street_lengths = get_street_lengths(streets)
    rand_index = choose_random_streets(street_lengths, count_veh)
    points = np.zeros(count_veh, dtype=object)

    if debug:
        time_diff = time.process_time() - time_start
        print_nnl(' {:.3f} seconds\n'.format(time_diff))

    if debug:
        time_start = time.process_time()
        print_nnl('Creating graphs for vehicles:')
    graphs_veh = np.zeros(count_veh, dtype=object)
    for iteration, index in enumerate(rand_index):
        street = streets.edges(data=True)[index]
        street_geom = street[2]['geometry']
        point = choose_random_point(street_geom)
        points[iteration] = point[0]
        # NOTE: All vehicle nodes get the prefix 'v'
        node = 'v' + str(iteration)
        # Add vehicle, needed intersections and edges to graph
        graph_iter = nx.MultiGraph(node_veh=node)
        node_attr = {'geometry': point[0], 'x' : point[0].x, 'y' : point[0].y}
        graph_iter.add_node(node, attr_dict=node_attr)
        graph_iter.add_nodes_from(street[0:1])

        street_before, street_after = split_line_at_point(street_geom, point[0])
        street_length = street_before.length
        edge_attr = {'geometry': street_before, 'length': street_length, 'is_veh_edge': True}
        graph_iter.add_edge(node, street[0], attr_dict=edge_attr)
        street_length = street_after.length
        edge_attr = {'geometry': street_after, 'length': street_length, 'is_veh_edge': True}
        graph_iter.add_edge(node, street[1], attr_dict=edge_attr)

        graphs_veh[iteration] = graph_iter.copy()

    x_coords, y_coords = extract_point_array(points)

    if debug:
        time_diff = time.process_time() - time_start
        print_nnl(' {:.3f} seconds\n'.format(time_diff))

    # Find center vehicle and plot
    if debug:
        time_start = time.process_time()
        print_nnl('Finding center vehicle:')
    index_center_veh = find_center_veh(x_coords, y_coords)
    index_other_vehs = np.ones(len(points), dtype=bool)
    index_other_vehs[index_center_veh] = False
    x_coord_center_veh = x_coords[index_center_veh]
    y_coord_center_veh = y_coords[index_center_veh]
    x_coord_other_vehs = x_coords[index_other_vehs]
    y_coord_other_vehs = y_coords[index_other_vehs]
    point_center_veh = points[index_center_veh]
    points_other_veh = points[index_other_vehs]
    plt.scatter(x_coord_center_veh, y_coord_center_veh, label='Own', marker='x', zorder=10, \
                s=2 * plt.rcParams['lines.markersize']**2, c='black')

    if debug:
        time_diff = time.process_time() - time_start
        print_nnl(' {:.3f} seconds\n'.format(time_diff))

    # Determine NLOS and OLOS/LOS
    if debug:
        time_start = time.process_time()
        print_nnl('Determining propagation condition:')
    is_nlos = veh_cons_are_nlos(point_center_veh, points_other_veh, buildings)
    x_coord_nlos_vehs = x_coord_other_vehs[is_nlos]
    y_coord_nlos_vehs = y_coord_other_vehs[is_nlos]

    if debug:
        time_diff = time.process_time() - time_start
        print_nnl(' {:.3f} seconds\n'.format(time_diff))

    # Determine OLOS and LOS
    if debug:
        print_nnl('Determining OLOS and LOS:')
        time_start = time.process_time()
    is_olos_los = np.invert(is_nlos)
    x_coord_olos_los_vehs = x_coord_other_vehs[is_olos_los]
    y_coord_olos_los_vehs = y_coord_other_vehs[is_olos_los]
    points_olos_los = points_other_veh[is_olos_los]
    # NOTE: A margin of 2, means round cars with radius 2 meters
    is_olos = veh_cons_are_olos(point_center_veh, points_olos_los, margin=2)
    is_los = np.invert(is_olos)
    x_coord_olos_vehs = x_coord_olos_los_vehs[is_olos]
    y_coord_olos_vehs = y_coord_olos_los_vehs[is_olos]
    x_coord_los_vehs = x_coord_olos_los_vehs[is_los]
    y_coord_los_vehs = y_coord_olos_los_vehs[is_los]
    plt.scatter(x_coord_los_vehs, y_coord_los_vehs, label='LOS', zorder=9, alpha=0.75)
    plt.scatter(x_coord_olos_vehs, y_coord_olos_vehs, label='OLOS', zorder=8, alpha=0.75)

    if debug:
        time_diff = time.process_time() - time_start
        print_nnl(' {:.3f} seconds\n'.format(time_diff))

    # Determine orthogonal and parallel
    if debug:
        time_start = time.process_time()
        print_nnl('Determining orthogonal and parallel:')

    graphs_veh_nlos = graphs_veh[index_other_vehs][is_nlos]
    graph_veh_own = graphs_veh[index_center_veh]
    is_orthogonal, coords_intersections = check_if_cons_orthogonal(streets_wave, graph_veh_own, \
                                                                   graphs_veh_nlos, \
                                                                   max_angle=np.pi)
    is_paralell = np.invert(is_orthogonal)
    x_coord_orth_vehs = x_coord_nlos_vehs[is_orthogonal]
    y_coord_orth_vehs = y_coord_nlos_vehs[is_orthogonal]
    x_coord_par_vehs = x_coord_nlos_vehs[is_paralell]
    y_coord_par_vehs = y_coord_nlos_vehs[is_paralell]

    if debug:
        time_diff = time.process_time() - time_start
        print_nnl(' {:.3f} seconds\n'.format(time_diff))

    plt.scatter(x_coord_orth_vehs, y_coord_orth_vehs, label='NLOS orth', zorder=5, alpha=0.5)
    plt.scatter(x_coord_par_vehs, y_coord_par_vehs, label='NLOS par', zorder=5, alpha=0.5)

    plt.legend()
    plt.xlabel('X coordinate [m]')
    plt.ylabel('Y coordinate [m]')
    plt.title('Vehicle positions and propagation conditions ({})'.format(place))

    # Determining pathlosses for LOS and OLOS
    if debug:
        time_start = time.process_time()
        print_nnl('Determining pathlosses for LOS and OLOS:')

    p_loss = pathloss.Pathloss()
    distances_olos_los = np.sqrt( \
        (x_coord_olos_los_vehs - x_coord_center_veh)**2 + \
        (y_coord_olos_los_vehs - y_coord_center_veh)**2)

    pathlosses_olos = p_loss.pathloss_olos(distances_olos_los[is_olos])
    pathlosses_los = p_loss.pathloss_los(distances_olos_los[is_los])

    pathlosses_olos_los = np.zeros(np.size(distances_olos_los))
    pathlosses_olos_los[is_olos] = pathlosses_olos
    pathlosses_olos_los[is_los] = pathlosses_los

    if debug:
        time_diff = time.process_time() - time_start
        print_nnl(' {:.3f} seconds\n'.format(time_diff))

    # Determining pathlosses for NLOS orthogonal
    if debug:
        time_start = time.process_time()
        print_nnl('Determining pathlosses for NLOS orthogonal:')

    # NOTE: Assumes center vehicle is receiver
    # NOTE: Uses airline vehicle -> intersection -> vehicle and not street route
    distances_orth_tx = np.sqrt(
        (x_coord_orth_vehs - coords_intersections[is_orthogonal, 0])**2 +
        (y_coord_orth_vehs - coords_intersections[is_orthogonal, 1])**2)

    distances_orth_rx = np.sqrt(
        (x_coord_center_veh - coords_intersections[is_orthogonal, 0])**2 +
        (y_coord_center_veh - coords_intersections[is_orthogonal, 1])**2)

    pathlosses_orth = p_loss.pathloss_nlos(distances_orth_rx, distances_orth_tx)

    pathlosses_nlos = np.zeros(np.size(x_coord_nlos_vehs))
    pathlosses_nlos[is_paralell] = np.Infinity*np.ones(np.sum(is_paralell))
    pathlosses_nlos[is_orthogonal] = pathlosses_orth

    # Build complete pathloss array
    pathlosses = np.zeros(count_veh-1)
    # TODO: Why - ? Fix in pathloss.py
    pathlosses[is_olos_los] = -pathlosses_olos_los
    pathlosses[is_nlos] = pathlosses_nlos

    if debug:
        time_diff = time.process_time() - time_start
        print_nnl(' {:.3f} seconds\n'.format(time_diff))

    # Plot streets and buildings
    fig, axi = plot_streets_and_buildings(data['streets'], data['buildings'], show=False, dpi=300)

    # Plot pathlosses
    index_wo_inf = pathlosses != np.Infinity
    index_inf = np.invert(index_wo_inf)
    plt.scatter(x_coord_center_veh, y_coord_center_veh, c='black', marker='x', label='Own', \
                s=2 * plt.rcParams['lines.markersize']**2)
    cax = plt.scatter(x_coord_other_vehs[index_wo_inf], y_coord_other_vehs[index_wo_inf], \
                      marker='o', c=pathlosses[index_wo_inf], cmap=plt.cm.magma, label='Finite PL')
    plt.scatter(x_coord_other_vehs[index_inf], y_coord_other_vehs[index_inf], marker='.', c='y', \
                      label='Infinite PL', alpha=0.5)
    axi.set_title('Vehicle positions and pathloss ({})'.format(place))
    plt.xlabel('X coordinate [m]')
    plt.ylabel('Y coordinate [m]')
    plt.legend()

    pl_min = np.min(pathlosses[index_wo_inf])
    pl_max = np.max(pathlosses[index_wo_inf])
    pl_med = np.mean((pl_min, pl_max))
    string_min = '{:.0f}'.format(pl_min)
    string_med = '{:.0f}'.format(pl_med)
    string_max = '{:.0f}'.format(pl_max)
    cbar = fig.colorbar(cax, ticks=[pl_min, pl_med, pl_max], orientation='vertical')
    cbar.ax.set_xticklabels([string_min, string_med, string_max])
    cbar.ax.set_xlabel('Pathloss [dB]')

    # Determine in range / out of range
    # Determining pathlosses for NLOS orthogonal
    if debug:
        time_start = time.process_time()
        print_nnl('Determining in range vehicles:')

    index_in_range = pathlosses < max_pl
    index_out_range = np.invert(index_in_range)

    if debug:
        time_diff = time.process_time() - time_start
        time_diff_tot = time.process_time() - time_start_tot
        print_nnl(' {:.3f} seconds\n'.format(time_diff))
        print_nnl('TOTAL RUNNING TIME: {:.3f} seconds\n'.format(time_diff_tot))

    # Plot streets and buildings
    fig, axi = plot_streets_and_buildings(data['streets'], data['buildings'], show=False, dpi=300)

    plt.scatter(x_coord_center_veh, y_coord_center_veh, c='black', marker='x', label='Own', \
                s=2 * plt.rcParams['lines.markersize']**2, zorder=3)
    plt.scatter(x_coord_other_vehs[index_in_range], y_coord_other_vehs[index_in_range], \
                marker='o', label='In range', zorder=2)
    plt.scatter(x_coord_other_vehs[index_out_range], y_coord_other_vehs[index_out_range], \
                marker='o', label='Out of range', alpha=0.75, zorder=1)

    plt.title('Vehicle positions and connectivity ({})'.format(place))
    plt.xlabel('X coordinate [m]')
    plt.ylabel('Y coordinate [m]')
    plt.legend()


    # Show the plots
    if debug:
        print('Showing plot')
    plt.show()

def parse_arguments():
    """Parses the command line arguments and returns them """
    parser = argparse.ArgumentParser(description='Simulate vehicle connections on map')
    parser.add_argument('-p', type=str, default='Neubau - Vienna - Austria', help='place')
    parser.add_argument('-c', type=int, default=1000, help='number of vehicles')
    parser.add_argument('-w', type=int, default=1, help='which result')
    arguments = parser.parse_args()
    return arguments

if __name__ == '__main__':
    args = parse_arguments()
    main_test(args.p, which_result=args.w, count_veh=args.c, max_pl=150, debug=True)
