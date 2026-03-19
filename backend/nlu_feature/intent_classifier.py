import math
import numpy as np
from preprocessing import nettoyer_phrase, nettoyer_dataset, charger_dataset

K_value = 3 #Pour l'algo KNN

#on appelle le resulat du chargement des données
contenu = charger_dataset()

#2 arguments car nettoyer dataset returne 2 valeurs
dataset_entrainement, vocabulaire_globale = nettoyer_dataset(contenu)


def vectoriser(phrase_commande, vocabulaire):
    vecteur = np.zeros(len(vocabulaire), dtype=int)
    for mot in phrase_commande:
        if mot in vocabulaire:
            indice = vocabulaire.index(mot)
            vecteur[indice] = 1

    return vecteur

def entrainer_modele(dataset, vocabulaire):

    #Matrice vide
    X_temp = []
    for ligne in dataset:
       mots_dataset = ligne[0]
       v_ligne = vectoriser(mots_dataset, vocabulaire)
       X_temp.append(v_ligne)
    
    return np.array(X_temp)


def prompt_user():
    sentence = input("Que voulez vous faire? \n")
    clean_sentence = nettoyer_phrase(sentence)
    v_user = vectoriser(clean_sentence, vocabulaire_globale)
    return print(v_user)

prompt_user()

X_train = entrainer_modele(dataset_entrainement, vocabulaire_globale)
print(X_train)