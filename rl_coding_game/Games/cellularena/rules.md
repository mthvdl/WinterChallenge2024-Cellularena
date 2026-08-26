## Full Statement (Converted)

## Objectif


Faites grandir votre organisme pour qu'il devienne le plus grand !


## Règles


Le jeu se déroule sur une grille.


### 🔵🔴 Les Organismes


Les Organismes sont composés d'organes occupant une case d'espace sur la grille de jeu.


Chaque joueur commence avec un organe de type ROOT. Votre organisme peut faire pousser (GROW) un nouvel organe à chaque tour afin de couvrir une plus large surface.


Un nouvel organisme peut pousser depuis n'importe quel organe existant, vers un emplacement adjacent libre.


Afin d'utiliser l'action GROW, votre organisme a besoin de protéines. Faire pousser 1 organe BASIC nécessite 1 protéine de type A.


Vous pouvez obtenir plus de protéines en faisant pousser un organe sur une case de la grille contenant une source de protéine ; celles-ci sont des cases avec une lettre à l'intérieur. Faire ceci vous octroiera 3 protéines du type correspondant.


Faites pousser plus d'organes que le Boss pour progresser vers la prochaine ligue.


Votre organisme peut recevoir les commandes suivantes:


- GROW id x y type: créé un nouvel organe à la position x, y depuis un organe ayant l'id id. Si la position cible n'est pas voisine de id, l'organe sera créé sur le plus court chemin vers x, y.


Cette commande va créer un nouvel organe BASIC depuis l'organe ROOT parent.


Voir la section Protocole de jeu pour plus d'informations sur l'envoi de commandes à votre organisme.


## Règles du HARVESTER


Cette commande crééra un nouveau HARVESTER faisant face à N (Nord).


Si un HARVESTER fait face à une case avec une source de protéines, vous recevrez 1 de cette protéine à chaque fin de tour.


Note : chaque joueur gagne seulement 1 protéine par source par tour, même si plusieurs HARVESTER sont dirigés vers cette source.


Pour faire pousser un HARVESTER, vous avez besoin de 1 protéine de type C et 1 protéine de type D.


## Règles du TENTACLE


À chaque tour, juste après la phase de récolte, chaque organe TENTACLE faisant face à un organe adverse l'attaquera, causant la mort de l'organe adverse. Les attaques se produisent simultanément.


Cette commande crééra un nouveau TENTACLE faisant face à E (Est), menant à l'attaque de l'organe adverse.


Quand un organe meurt, tout ses enfants meurent également. Cela se propagera à tout l'organisme si le ROOT est ainsi détruit.


Note: Vous pouvez utiliser la variable organParentId pour recenser les enfants de chaque organe.


Un tentacule empêche également l'adversaire de faire pousser un organe sur la case en face de celui-ci.


Pour faire pousser un TENTACLE vous avez besoin de 1 protéine de type B et 1 protéine de type C.


## Règles du SPORER


L'organe  de type SPORER est unique de deux manières :


- Il est le seul organe pouvant créer un nouvel organe ROOT.

- Pour créer un nouveau ROOT, il projette une spore en ligne droite, vous permettant de placer le nouvel organe ROOT sur n'importe quelle case libre lui faisant face.


Note: un organe ROOT n'a jamais de parent, même s'il a été créé depuis un SPORER.


Cette commande permettra au SPORER de créer un nouveau ROOT vers le Sud.


Lorsque vous contrôlez plusieurs organismes, vous devez envoyer une commande pour chacun d'eux. Ils effectueront leurs actions de manière simultanée.


La variable requiredActionsCount représente le nombre d'organismes que vous contrôlez. Vous devez utiliser la commande WAIT pour chaque organisme qui ne peut agir.


Note : Vous pouvez utiliser la variable organRootId pour déterminer quels organes appartiennent au même organisme.


Pour faire pousser un SPORER vous avez besoin de 1 protéine de type B et 1 protéine de type D.


Pour produire un nouveau ROOT vous avez besoin de 1 protéine de chaque type.


Voici une table résumant les coûts des différents organes :


Organe
A
B
C
D


BASIC
1
0
0
0


HARVESTER
0
0
1
1


TENTACLE
0
1
1
0


SPORER
0
1
0
1


ROOT
1
1
1
1


### ⛔ Fin du jeu


Le jeu se termine quand il détecte qu'aucun progrès ne peut plus être fait ou après 100 tours.


### 🎬 Ordre des actions pour un tour


- Les actions GROW et SPORE sont calculées.


- Les murs issus de collisions sont générés.


- Les récoltes de protéines sont calculées.


- Les attaques de tentacules sont calculées.


- Les conditions de fin de partie sont vérifiées.


Conditions de victoire


Le gagnant est le joueur ayant le plus de cases occupées par un de ses organes.


Conditions de défaite


Votre programme ne fournit pas une commande dans le temps imparti ou fournit une commande non reconnue.


### 🐞 Conseils de débogage


- Survolez la grille pour voir plus d'informations sur les organes sous votre curseur.

- Ajoutez du texte à la fin d'une instruction pour afficher ce texte au dessus de votre organisme.

- Cliquez sur la roue dentée pour afficher les options visuelles supplémentaires.

- Utilisez le clavier pour contrôler l'action : espace pour play / pause, les flèches pour avancer pas à pas.


## Protocole de jeu


Entrées d'Initialisation


Première ligne : deux entiers width et height pour la taille de la grille.


Entrées pour un tour de jeu


Première ligne : un entier entityCount pour le nombre d'entités sur la grille.

Prochaines entityCount lignes : Les 7 entrées suivantes pour chaque entité :


- x : Position X (0 commence à gauche)

- y : Position Y (0 commence en haut)

- type :


  - WALL pour un mur

  - ROOT pour un organe de type ROOT

  - BASIC pour un organe de type BASIC

  - HARVESTER pour un organe de type HARVESTER

  - TENTACLE pour un organe de type TENTACLE

  - SPORER pour un organe de type SPORER

  - A pour une source de protéine A

  - B pour une source de protéine B

  - C pour une source de protéine C

  - D pour une source de protéine D


- owner :


  - 1 si vous êtes le propriétaire de cet organe

  - 0 si votre adversaire est le propriétaire de cet organe

  - -1 si cette entité n'est pas un organe


- organId : id unique de cette entité si c'est un organe, 0 sinon.

- organDir : N, W, S, ou E pour la direction vers laquelle cet organe fait face

- organParentId : si c'est un organe, l'organId de l'organe dont cet organe est issu (0 pour les organes ROOT), 0 sinon.

- organRootId : si c'est un organe, l'organId de l'organe ROOT ancêtre de cet organe, 0 sinon.


Prochaine ligne : 4 entiers : myA,myB,myC,myD pour les quantités de chaque protéine que vous possédez.


Prochaine ligne : 4 entiers : oppA,oppB,oppC,oppD pour les quantités de chaque protéine que votre adversaire possède.


Prochaine ligne : un entier requiredActionsCount égal au nombre de commandes que vous avez à entrer pour ce tour.


Sortie


- GROW id x y type direction : tenter de faire pousser un nouvel organe de type type à la position x, y depuis l'organe id. Si la position cible n'est pas voisine de id, l'organe sera créé sur le plus court chemin vers x, y.


- SPORE id x y : tenter de créer un nouvel organe ROOT à la position x, y depuis le SPORER id.


- WAIT : ne rien faire.


Ajoutez du texte après votre commande et celui-ci sera affiché sur le viewer.


Contraintes


Temps de réponse par tour ≤ 50ms

Temps de réponse pour le premier tour ≤ 1000ms

16 ≤ width ≤ 24

8 ≤ height ≤ 12
