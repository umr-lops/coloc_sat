import os


class OpenEra5:
    def __init__(self, product_path):
        self.product_path = product_path
        self.product_name = os.path.basename(self.product_path)
