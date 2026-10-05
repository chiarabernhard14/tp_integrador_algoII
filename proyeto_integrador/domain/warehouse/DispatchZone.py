class DispatchZone:

    def __init__(self, nodes, door, width, height):
        self.start_node = nodes[0]
        self.end_node = nodes[1]
        self.width = width
        self.height = height
        self.door = door
