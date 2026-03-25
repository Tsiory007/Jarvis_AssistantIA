import json
import os


def charger_contact():
    path = os.path.join(os.path.dirname(__file__), "contact.json")
    try:
        with open (path, 'r', encoding='utf-8') as f:
            repertoire = json.load(f)
        return repertoire
    except FileNotFoundError as e:
        print("Erreur lors de du chargement du fichier")
        return {}
    
