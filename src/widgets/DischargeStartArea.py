from uuid import uuid4


class DischargeStartArea:
    def __init__(self, timestamp, x, y, width, height, involved_channels):
        self.id = uuid4().__str__()
        self.timestamp = timestamp
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.involved_channels = involved_channels

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "involved_channels": [
                [cell.row, cell.col] for cell in self.involved_channels
            ],
        }

    def __str__(self):
        return f"Discharge:\n\tTime: {self.timestamp} s\n\t(x, y): ({self.x}, {self.y})\n\t(w, h): ({self.width}, {self.height}))"
