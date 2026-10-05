class Aisle:

    def __init__(self, start_node=None, end_node=None, direction=""):
        self.start_node = start_node
        self.end_node = end_node

        #Los nodos ya están validados en este punto

        if self.end_node[1]  == self.start_node[1]:
            self.length = abs(self.end_node[0] - self.start_node[0])
            self.direction = "HORIZONTAL"
        else: 
            self.length = abs(self.end_node[1] - self.start_node[1])
            self.direction = "VERTICAL"

