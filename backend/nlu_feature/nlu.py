import pandas as pd
import numpy as np
import string

#Lecture du fichier (dataset) 
def charger_dataset():
    try: 
        with open ('dataset.csv', 'r', encoding='utf-8') as f:
            data = f.read()       
        print("Fichier chargé avec succès")
        print(data)
        return data

    except FileNotFoundError: 
        print("Erreur, fichier non trouvé")

    except Exception as e:
        print("Une erreur est survenue")   

#Nettoyage input user pour le test
def nettoyer_phrase():  #lowercase puis supprimer ponctuation, et enfin split la phrase
    ponctuation = string.punctuation
    phrase = str(input("Entrez une commande:\n")).lower()
    for symbole in ponctuation:
        phrase = phrase.replace(symbole,"")
    resultat = phrase.split()
    print(resultat)
    

#fonction de nettoyage
def nettoyer_donnees(dataset_brute):
    if dataset_brute is None:
        return
    
    donnees_stockees = []
    stop_words = ["mba", "ny","azafady","kely","hoe"]
    
    #separation des donnees par lignes
    lignes = dataset_brute.split("\n")
    print("Nb de lignes: ", {len(lignes)})
    

    #separation des actions et commandes
    for ligne in lignes:
        if not ligne or ',' not in ligne:
            continue

        #decouper l'action par ,
        action = ligne.split(",")

        #on nettoye d'abord le texte (miniscule, espace inutile)
        phrase_propre = action[0].lower().strip()
        ponctuation = string.punctuation
        for symbole in ponctuation:
            phrase_propre = phrase_propre.replace(symbole,"")

            #On le divise en dernier lieu apres avoir tout fait
            mots_liste = phrase_propre.split()

            #garder le mot dans la liste si le mot n'est pas dans stop words
            mots_filtre = [mot for mot in mots_liste if mot not in stop_words]
        donnees_stockees.append([mots_filtre, action[1].strip()])

    print("Nettoyage terminé")
    print(donnees_stockees)


donnees_brute = charger_dataset()
nettoyer_donnees(donnees_brute)


"""Prochaine etape:
 Lister les mots uniques du dataset
 Debuter l'algorithme des K plus proche voisin 
 """