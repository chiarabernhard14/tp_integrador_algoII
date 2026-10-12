from validation import validate_segment   

class LinearElement:
    
    def __init__(self, start_node, end_node):
        self._start_node, self._end_node = validate_segment(start_node, end_node)

    @property
    def start_node(self):
        return self._start_node

    @property
    def end_node(self):
        return self._end_node

    @property
    def direction(self):
        if self._start_node[1] == self._end_node[1]:
            return "HORIZONTAL"
        return "VERTICAL"

    @property
    def length(self):
        if self.direction == "HORIZONTAL":
            return self._end_node[0] - self._start_node[0]
        return self._end_node[1] - self._start_node[1]

    def cells(self):
        x1, y1 = self._start_node
        x2, y2 = self._end_node
        return [(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)]

    def __repr__(self):
        return f"{type(self).__name__}({self._start_node}, {self._end_node})"