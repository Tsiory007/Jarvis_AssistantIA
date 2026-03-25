import os
import sys
from pathlib import Path 
from nlu_feature.intent_classifier import interpreter_commande
from nlu_feature.execution import executer_commande
from nlu_feature.audio_service import jouer_audio_aleatoire


BASE_DIR = Path(__file__).resolve().parent.parent
chemin_services = BASE_DIR / "Jarvis" / "services"

sys.path.append(str(chemin_services))
from AskJarvis import ask_jarvis # type: ignore


def main(commande):
    print("SYSTEME JARVIS ACTIVÉ")
    try:
        resultat = interpreter_commande(commande)
        print(resultat)
        if resultat:
            resulat_knn, phrase_user = resultat

        #Verifier si le KNN a compris la commande
        if resulat_knn is not None:
            executer_commande(resulat_knn, phrase_user)

        else:
            #Le KNN n'as pas compris
            jouer_audio_aleatoire("filler")
            
            if ask_jarvis:
                #Recoller si on a une liste pour l'envoyer a l'api
                phrase = " ".join(phrase_user) if isinstance(phrase_user,list) else phrase_user
                reponse_jarvis = ask_jarvis(phrase)
                
                if reponse_jarvis:
                    print(f"Jarvis: {reponse_jarvis}")
                    out_path = os.path.join(os.path.dirname(__file__),"..", "Jarvis", "services", "reponse_ia", "ia.txt")
                    try:
                        with open(out_path, "w", encoding="utf-8") as tf:
                            tf.write(reponse_jarvis)
                        print(f" Réponse ai sauvegardée")
                    except Exception as e:
                        print(f"Erreur écriture txt: {repr(e)}")
                        return
                else: 
                     jouer_audio_aleatoire("confused")
                     print("Désolé, je ne connais pas la reponse à votre question.")
                     
    except KeyboardInterrupt:
        print("Jarvis mise en veille. À bientôt !")
    except Exception as e:
        print(f"Une erreur est surveue",e)


        
if __name__ == "__main__":
        main("Hey")