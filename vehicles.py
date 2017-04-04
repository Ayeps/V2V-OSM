""" Distributes vehicles along streets"""

import numpy as np
import geometry as geom_o
import networkx as nx


class Vehicles:
    """Class representing vehicles with their properties and relations to each other"""
    # TODO: only points as attributes and get coordinates from points when
    # requested?

    def __init__(self, points, graphs=None, size=0):
        self.count = np.size(points)
        self.points = points
        self.coordinates = geom_o.extract_point_array(points)
        self.graphs = graphs
        self.pathlosses = np.zeros(size)
        self.distances = np.zeros(size)
        self.nlos = np.zeros(size, dtype=bool)
        self.idxs = {}

    def allocate(self, size):
        """Allocate memory for releational properties"""

        self.pathlosses = np.zeros(size)
        self.distances = np.zeros(size)
        self.nlos = np.zeros(size, dtype=bool)

    def add_key(self, key, value):
        """Add a key that can then be used to retrieve a subset of the properties/relations"""

        self.idxs[key] = value

    def get(self, key=None):
        """"Get the coordinates of a set of vehicles specified by a key"""

        if key is None:
            return self.coordinates
        else:
            return self.coordinates[self.idxs[key]]

    def get_points(self, key=None):
        """"Get the geometry points of a set of vehicles specified by a key"""

        if key is None:
            return self.points
        else:
            return self.points[self.idxs[key]]

    def get_graph(self, key=None):
        """"Get the graphs of a set of vehicles specified by a key"""

        if key is None:
            return self.graphs
        else:
            return self.graphs[self.idxs[key]]

    def get_idxs(self, key):
        """Get the indices defined by a key"""

        return self.idxs[key]

    def set_pathlosses(self, key, values):
        """"Set the pathlosses of a set of relations specified by a key"""

        self.pathlosses[self.idxs[key]] = values

    def get_pathlosses(self, key=None):
        """"Get the pathlosses of a set of relations specified by a key"""

        if key is None:
            return self.pathlosses
        else:
            return self.pathlosses[self.idxs[key]]

    def set_distances(self, key, values):
        """"Set the distances of a set of relations specified by a key"""

        self.distances[self.idxs[key]] = values

    def get_distances(self, key=None):
        """"Get the distances of a set of relations specified by a key"""

        if key is None:
            return self.distances
        else:
            return self.distances[self.idxs[key]]


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


def generate_vehs(graph_streets, street_idxs):
    """Generates vehicles on specific streets """

    count_veh = np.size(street_idxs)
    points_vehs = np.zeros(count_veh, dtype=object)
    graphs_vehs = np.zeros(count_veh, dtype=object)

    for iteration, index in enumerate(street_idxs):
        street = graph_streets.edges(data=True)[index]
        street_geom = street[2]['geometry']
        point_veh = choose_random_point(street_geom)
        points_vehs[iteration] = point_veh[0]
        # NOTE: All vehicle nodes get the prefix 'v'
        node = 'v' + str(iteration)
        # Add vehicle, needed intersections and edges to graph
        graph_iter = nx.MultiGraph(node_veh=node)
        node_attr = {'geometry': point_veh[
            0], 'x': point_veh[0].x, 'y': point_veh[0].y}
        graph_iter.add_node(node, attr_dict=node_attr)
        graph_iter.add_nodes_from(street[0:2])

        # Determine street parts that connect vehicle to intersections
        street_before, street_after = geom_o.split_line_at_point(
            street_geom, point_veh[0])
        edge_attr = {'geometry': street_before,
                     'length': street_before.length, 'is_veh_edge': True}
        graph_iter.add_edge(node, street[0], attr_dict=edge_attr)
        edge_attr = {'geometry': street_after,
                     'length': street_after.length, 'is_veh_edge': True}
        graph_iter.add_edge(node, street[1], attr_dict=edge_attr)

        # Copy the created graph
        graphs_vehs[iteration] = graph_iter.copy()

    vehs = Vehicles(points_vehs, graphs_vehs)
    return vehs