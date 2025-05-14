from exportVolume import get_export_volume
from exportPreco import get_export_preco
from exportReceita import get_export_receita
import pandas as pd

def update_data():
    export_volume = get_export_volume()
    export_preco = get_export_preco()
    export_receita = get_export_receita()
    