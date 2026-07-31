<!-- LEAGUES level1 level2 level3 level4 level5 -->
<!-- BEGIN level1 level2 level3 level4 -->
<div id="statement_back" class="statement_back" style="display: none"></div>
<div class="statement-body">
  <!-- LEAGUE ALERT -->
  <div style="color: #7cc576; 
  background-color: rgba(124, 197, 118,.1);
  padding: 20px;
  margin-right: 15px;
  margin-left: 15px;
  margin-bottom: 10px;
  text-align: left;">
  <div style="text-align: center; margin-bottom: 6px">
    <img src="//cdn.codingame.com/smash-the-code/statement/league_wood_04.png" />
  </div>
  <p style="text-align: center; font-weight: 700; margin-bottom: 6px;">
    Ce challenge est basé sur un système de ligues.
  </p>
  <span class="statement-league-alert-content">
    Pour ce challenge, plusieurs ligues pour le même jeu seront disponibles. Quand vous aurez prouvé votre valeur contre le premier Boss, vous accéderez à la ligue supérieure et débloquerez de nouveaux adversaires.
    <br><br>
    <b>NOUVEAU :</b> votre bot se battera uniquement avec le Boss une fois dans l'arène. Gagnez plus souvent que lui sur 5 matchs pour avancer jusqu'à la ligue finale.
  </span>
</div>

<!-- BEGIN level4 -->
<div class="statement-section statement-goal">
  <h2>
    <span class="icon icon-goal">&nbsp;</span>
    <span>Félicitations</span>
  </h2>
  <div class="statement-goal-content">
    
    <p>
      Votre organisme peut <b>combattre</b>!
    </p>
    
    <p>
      Cependant, votre organisme est resté <b>seul</b> jusqu'alors. Mais avec le pouvoir de l'organe de type <action>SPORER</action>, vous pouvez faire pousser de <b>nouveaux organismes</b>.
    </p>
    
    <div style="text-align: center; margin: 15px">
      
      <img src="https://static.codingame.com/servlet/fileservlet?id=132396021519497"
      alt="Grow your organism to become the largest!" />
      <div style="margin: auto; width: 400px; max-width: 100%"><em>L'organe SPORER.</em></div>
    </div>
  </div>
</div>

<div class="statement-section statement-rules">
  <h2>
    <span class="icon icon-rules">&nbsp;</span>
    <span>Règles du SPORER</span>
  </h2>
  
  <div class="statement-rules-content">
    <p>
      L'organe de type <action>SPORER</action> est unique de deux manières :
      <ul>
        <li>Il est le seul organe pouvant créer un nouvel organe <action>ROOT</action>.</li>
        <li>Pour créer un nouveau <action>ROOT</action>, il projette une spore en ligne droite, vous permettant de placer le nouvel organe <action>ROOT</action> sur n'importe quelle case libre lui faisant face.</li>
      </ul>
    </p>
    
    <p><em>Note : un organe <action>ROOT</action> n'a jamais de <b>parent</b>, même s'il a été créé depuis un <action>SPORER</action>.</em></p>
    <br>
    
    
    <div style="text-align: center; margin: 15px">
      <img src="https://static.codingame.com/servlet/fileservlet?id=132395742195955"
      style="width: 400px; max-width: 100%" />
      <div style="margin: auto; width: 400px; max-width: 100%"><em>Cette commande permettra au <action>SPORER</action> de créer un nouveau <action>ROOT</action> vers le Sud.</em></div>
    </div>
    
    
    <p>Lorsque vous contrôlez <b>plusieurs</b> organismes, vous devez envoyer une commande pour <b>chacun d'eux</b>. Ils effectueront leurs actions de manière simultanée.</p>
    <br>
    
    <p>La variable <var>requiredActionsCount</var> représente le nombre d'organismes que vous contrôlez. Vous <b>devez</b> utiliser la commande <action>WAIT</action> pour chaque organisme qui ne peut agir.</p>
    <br>
    
    <p><em>Note : Vous pouvez utiliser la variable <var>organRootId</var> pour déterminer quels organes appartiennent au même organisme.</em></p>
    <br>
    
    <p>Pour faire pousser un <action>SPORER</action> vous avez besoin de <const>1</const> protéine de type <var>B</var> et <const>1</const> protéine de type <var>D</var>.</p>
    <p>Pour produire un nouveau <action>ROOT</action> vous avez besoin de <const>1</const> protéine de chaque type.</p>
    <br>
    
    <p>Voici une table résumant les coûts des différents organes :</p>
    <table style="margin-bottom: 20px">
      <thead>
        <tr>
          <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">Organe</th>
          <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">A</th>
          <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">B</th>
          <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">C</th>
          <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">D</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="padding: 5px;outline: 1px solid #838891;"><action>BASIC</action></td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
          <td style="padding: 5px;outline: 1px solid #838891;">0</td>
          <td style="padding: 5px;outline: 1px solid #838891;">0</td>
          <td style="padding: 5px;outline: 1px solid #838891;">0</td>
        </tr>
        <tr>
          <td style="padding: 5px;outline: 1px solid #838891;"><action>HARVESTER</action></td>
          <td style="padding: 5px;outline: 1px solid #838891;">0</td>
          <td style="padding: 5px;outline: 1px solid #838891;">0</td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
        </tr>
        <tr>
          <td style="padding: 5px;outline: 1px solid #838891;"><action>TENTACLE</action></td>
          <td style="padding: 5px;outline: 1px solid #838891;">0</td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
          <td style="padding: 5px;outline: 1px solid #838891;">0</td>
        </tr>
        <tr>
          <td style="padding: 5px;outline: 1px solid #838891;"><action>SPORER</action></td>
          <td style="padding: 5px;outline: 1px solid #838891;">0</td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
          <td style="padding: 5px;outline: 1px solid #838891;">0</td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
        </tr>
        <tr>
          <td style="padding: 5px;outline: 1px solid #838891;"><action>ROOT</action></td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
          <td style="padding: 5px;outline: 1px solid #838891;">1</td>
        </tr>
      </tbody>
    </table>
    
    
    
    <!-- BEGIN level4 -->
    <p> Dans cette ligue, il y a <b>une</b> source de protéines, mais votre organisme de départ n'est pas assez proche pour la <b>récolter</b>.
    </p>
    <!-- END -->
    <p>
      <b>Utilisez un <action>SPORER</action> pour produire un nouveau <action>ROOT</action> vers la protéine et croître plus vite que votre adversaire !</b></p>
      
      <!-- BEGIN level4 -->
      <br>
      <p><em>De nouvelles informations ont été ajoutées à la section <b>Protocole de jeu</b>.</em></p>
      <!-- END -->
    </div>
  </div>
  <!-- END -->
  
  <!-- BEGIN level3 -->
  <div class="statement-section statement-goal">
    <h2>
      <span class="icon icon-goal">&nbsp;</span>
      <span>Félicitations</span>
    </h2>
    <div class="statement-goal-content">
      
      <p>
        Votre organisme peut <b>récolter</b>!
      </p>
      
      <p>
        Cependant, <b>votre adversaire</b> sera parfois <b>en travers de votre chemin</b>. Faites-leur goûter à votre organe de type <action>TENTACLE</action>.
      </p>
      
      <div style="text-align: center; margin: 15px">
        
        <img src="https://static.codingame.com/servlet/fileservlet?id=132395883395976"
        alt="Grow your organism to become the largest!" />
        <div style="margin: auto; width: 400px; max-width: 100%"><em>L'organe TENTACLE.</em></div>
      </div>
    </div>
  </div>
  
  <!-- END -->
  
  <!-- BEGIN level3 level4 -->
  <div class="statement-section statement-rules">
    <h2>
      <span class="icon icon-rules">&nbsp;</span>
      <span>Règles du TENTACLE</span>
    </h2>
    
    <div class="statement-rules-content">
      À chaque tour, juste après la phase de <b>récolte</b>, chaque organe <action>TENTACLE</action> faisant face à un organe adverse l'<b>attaquera</b>, causant la <b>mort</b> de l'organe adverse. Les attaques se produisent simultanément.
    </div>
    
    <div style="text-align: center; margin: 15px">
      <img src="https://static.codingame.com/servlet/fileservlet?id=132395781400673"
      style="width: 400px; max-width: 100%" />
      <div style="margin: auto; width: 400px; max-width: 100%"><em>Cette commande crééra un nouveau <action>TENTACLE</action> faisant face à <var>E</var> (Est), menant à l'attaque de l'organe adverse.</em></div>
    </div>
    
    
    <p>Quand un organe <b>meurt,</b> tout ses <b>enfants</b> meurent également. Cela se propagera à <b>tout</b> l'organisme si le <action>ROOT</action> est ainsi détruit.</p>
    <br>
    
    <p><em>Note : Vous pouvez utiliser la variable <var>organParentId</var> pour recenser les enfants de chaque organe.</em></p>
    <br>
    
    <p>Un tentacule empêche également l'adversaire de faire pousser un organe sur la case en face de celui-ci.</p>
    <br>
    
    <p>Pour faire pousser un <action>TENTACLE</action> vous avez besoin de <const>1</const> protéine de type <var>B</var> et <const>1</const> protéine de type <var>C</var>.</p>
    <br>
    <!-- BEGIN level3 -->
    <p> Dans cette ligue, il n'y a aucune <b>source de protéines</b>, mais vous commencez avec un stock rempli de diverses protéines.
      <br>
      <!-- END -->
      <b>Utilisez-les pour faire pousser un large organisme et attaquer l'organisme adverse !</b></p>
      
      <!-- BEGIN level3 -->
      <br>
      <p><em>De nouvelles informations ont été ajoutées à la section <b>Protocole de jeu.</em></p>
        <!-- END -->
        
      </div>
      
      <!-- END -->
      
      <!-- BEGIN level2 -->
      <div class="statement-section statement-goal">
        <h2>
          <span class="icon icon-goal">&nbsp;</span>
          <span>Congratulations</span>
        </h2>
        <div class="statement-goal-content">
          
          <p>
            Votre organisme peut <b>croître</b> !
          </p>
          
          <p>
            Cependant, les <b>sources de protéines</b> sur la grille sont limitées, et une fois que vous les absorbez, celles-ci disparaissent. C'est là que le type d'organe <action>HARVESTER</action> entre en jeu.
          </p>
          
          <div style="text-align: center; margin: 15px">
            
            <img src="https://static.codingame.com/servlet/fileservlet?id=132395829688056"
            alt="Grow your organism to become the largest!" />
            <div style="margin: auto; width: 400px; max-width: 100%"><em>L'organe HARVESTER.</em></div>
          </div>
        </div>
      </div>
      <!-- END -->
      <!-- BEGIN level2 level3 level4 -->
      <div class="statement-section statement-rules">
        <h2>
          <span class="icon icon-rules">&nbsp;</span>
          <span>Règles du HARVESTER</span>
        </h2>
        
        <!-- BEGIN level2 -->
        <div class="statement-rules-content">
          À partir de cette ligue, les organes que vous placez auront une <var>direction</var>.
        </div>
        <!-- END -->
        
        <div style="text-align: center; margin: 15px">
          <img src="https://static.codingame.com/servlet/fileservlet?id=132395760074979"
          style="width: 400px; max-width: 100%" />
          <div style="margin: auto; width: 400px; max-width: 100%"><em>Cette commande crééra un nouveau <action>HARVESTER</action> faisant face à <var>N</var> (Nord).</em></div>
        </div>
        
        <p>Si un <action>HARVESTER</action> fait face à une case avec une <b>source de protéines</b>, vous recevrez <const>1</const> de cette protéine à <b>chaque fin de tour</b>.</p>
        <br>
        <p><em>Note : chaque joueur gagne seulement <const>1</const> protéine par source par tour, même si plusieurs <action>HARVESTER</action> sont dirigés vers cette source.</em></p>
        
        <br>
        <p>Pour faire pousser un <action>HARVESTER</action>, vous avez besoin de <const>1</const> protéine de type <var>C</var> et <const>1</const> protéine de type <var>D</var>.</p>
        <!-- BEGIN level2 -->
        <br>
        <p> Dans cette ligue, on vous fourni <const>1</const> protéine de type <var>C</var> et <const>1</const> protéine de type <var>D</var>, <b>utilisez-les pour faire pousser un <action>HARVESTER</action> à l'endroit adapté pour faire croître votre organisme indéfiniment !</b></p>
        <!-- END -->
        
        <!-- BEGIN level2 -->
        <br>
        <p><em>De nouvelles informations ont été ajoutées à la section <b>Protocole de jeu.</b></em></p>
        <!-- END -->
        
      </div>
      <!-- END -->
      
      <!-- GOAL -->
      <!-- BEGIN level1 -->
      <div class="statement-section statement-goal">
        <h2>
          <span class="icon icon-goal">&nbsp;</span>
          <span>Objectif</span>
        </h2>
        <div class="statement-goal-content">
          <div>
            Faites grandir votre organisme pour qu'il devienne le plus grand !
          </div>
          
          <div style="text-align: center; margin: 15px">
            <img src="https://static.codingame.com/servlet/fileservlet?id=132396041223454"
            alt="Grow your organism to become the largest!" style="width: 60%; max-width: 300px" />
          </div>
        </div>
      </div>
      <!-- END -->
      
      <!-- RULES -->
      <div class="statement-section statement-rules">
        <h2>
          <span class="icon icon-rules">&nbsp;</span>
          <span>Règles</span>
        </h2>
        
        <div class="statement-rules-content">
          <p>Le jeu se déroule sur une grille.<br><br>
            Pour les premières ligues, il suffit de battre le Boss dans des situations spécifiques.
          </p>
          <br>
          
          <h3 style="font-size: 14px;
          font-weight: 700;
          padding-top: 5px;
          padding-bottom: 15px;">
          🔵🔴 Les Organismes</h3>
          
          <p>Les <b>Organismes</b> sont composés d'<b>organes</b> occupant <const>une</const> case d'espace sur la grille de jeu.</p>
          
          <br>
          <!-- BEGIN level1 -->
          <p>Chaque joueur commence avec un organe de type <var>ROOT</var>. Dans cette ligue, votre organisme peut faire pousser (<action>GROW</action>) un nouvel organe de type <var>BASIC</var> à chaque tour afin de couvrir une plus large surface.</p>
          <!-- END -->
          <!-- BEGIN level2 level3 level4 -->
          <p>Chaque joueur commence avec un organe de type <var>ROOT</var>. Votre organisme peut faire pousser (<action>GROW</action>) un nouvel organe à chaque tour afin de couvrir une plus large surface.</p>
          <!-- END -->
          
          <br/>
          <p>Un nouvel organe peut pousser <b>depuis</b> n'importe quel <b>organe</b> existant, vers un <b>emplacement adjacent libre</b>.</p>
          <br>
          
          <!-- BEGIN level1 -->
          <p> Afin d'utiliser l'action <action>GROW</action>, votre organisme a besoin de <b>protéines</b>.</p>
          <p>    Dans cette ligue, vous débutez le jeu avec <const>10</const> protéines de type <var>A</var>. Faire pousser 1 organe <var>BASIC</var> nécessite <const>1</const> de ces protéines.
          </p>
          <!-- END -->
          <!-- BEGIN level2 level3 level4 -->
          <p> Afin d'utiliser l'action <action>GROW</action>, votre organisme a besoin de <b>protéines</b>. Faire pousser 1 organe <var>BASIC</var> nécessite <const>1</const> protéine de type A.
          </p>
          <!-- END -->
          <br/>
          <p>
            Vous pouvez obtenir plus de <b>protéines</b> en faisant pousser un organe sur une case de la grille contenant une <b>source de protéine</b> ; celles-ci sont des cases avec une lettre à l'intérieur. Faire ceci vous octroiera <const>3</const> protéines du type correspondant.
          </p>
          <br>
          
          <br>
          
          <p>Votre organisme peut recevoir les commandes suivantes:</p>
          
          <ul>
            <li>
              <action>GROW id x y type</action>: créé un nouvel organe à la position <var>x</var>, <var>y</var> depuis un organe ayant l'id <var>id</var>. Si la position cible n'est pas voisine de <var>id</var>, l'organe sera créé sur le plus court chemin vers <var>x</var>, <var>y</var>.
              
              <div style="text-align: center; margin: 15px">
                <img src="https://static.codingame.com/servlet/fileservlet?id=132395721182727"
                style="width: 400px; max-width: 100%" />
                <div style="margin: auto; width: 400px; max-width: 100%"><em>Cette commande va créer un nouvel organe <var>BASIC</var> depuis l'organe <var>ROOT</var> parent.</em></div>
              </div>
            </li>
            
            
          </ul>
          <br>
          
          <p>Voir la section <b>Protocole de jeu</b> pour plus d'informations sur l'envoi de commandes à votre organisme.</p>
          <br>
          
          <br>
          <h3 style="font-size: 14px;
          font-weight: 700;
          padding-top: 5px;
          padding-bottom: 15px;">
          ⛔ Fin du jeu</h3>
          
          <p>
            Le jeu se termine quand il détecte qu'aucun progrès ne peut plus être fait ou après <const>100</const> tours.<br>
            <br>
          </p>
          
          <!-- Victory conditions -->
          <div class="statement-victory-conditions">
            <div class="icon victory"></div>
            <div class="blk">
              <div class="title">Conditions de victoire</div>
              <div class="text">
                <ul style="padding-top:0; padding-bottom: 0;">
                  Le gagnant est le joueur ayant le plus de cases occupées par un de ses organes.
                </ul>
              </div>
            </div>
          </div>
          <!-- Lose conditions -->
          <div class="statement-lose-conditions">
            <div class="icon lose"></div>
            <div class="blk">
              <div class="title">Conditions de défaite</div>
              <div class="text">
                <ul style="padding-top:0; padding-bottom: 0;">
                  Votre programme ne fournit pas une commande dans le temps imparti ou fournit une commande non reconnue.
                </ul>
              </div>
            </div>
          </div>
          <br>
          <h3 style="font-size: 14px;
          font-weight: 700;
          padding-top: 5px;
          padding-bottom: 15px;">
          🐞 Conseils de débogage</h3>
          <ul>
            <li>Survolez la grille pour voir plus d'informations sur les organes sous votre curseur.</li>
            <li>Ajoutez du texte à la fin d'une instruction pour afficher ce texte au dessus de votre organisme.</li>
            <li>Cliquez sur la roue dentée pour afficher les options visuelles supplémentaires.</li>
            <li>Utilisez le clavier pour contrôler l'action : espace pour play / pause, les flèches pour avancer pas à pas.</li>
          </ul>
        </div>
      </div>
      
      
      <!-- PROTOCOL -->
      <!-- BEGIN level1 -->
      <details class="statement-section statement-protocol">
        <!-- END -->
        <!-- BEGIN level2 level3 level4 -->
        <details open class="statement-section statement-protocol">
          <!-- END -->
          <summary 
          open
          style="cursor: pointer; margin-bottom: 10px;display: inline-block;">
          
          <span style="display: inline-block; margin-bottom: 10px;">Cliquez pour agrandir</span>
          <h2 style="margin-bottom: 0;">
            <span class="icon icon-protocol">&nbsp;</span>
            <span>Protocole de jeu</span>
          </h2>
        </summary>
        <!-- Protocol block -->
        <div class="blk">
          <div class="title">Entrées d'Initialisation</div>
          <div class="text">
            <span class="statement-lineno">Première ligne :</span> deux entiers <var>width</var> et <var>height</var> pour la taille de la grille.<br>
          </div>
        </div>
        <!-- Protocol block -->
        <div class="blk">
          <div class="title">Entrées pour un tour de jeu</div>
          <div class="text">
            <span class="statement-lineno">Première ligne :</span> un entier <var>entityCount</var> pour le nombre d'entités sur la grille.<br>
            <span class="statement-lineno">Prochaines <var>entityCount</var> lignes :</span> Les <const>7</const> entrées suivantes pour chaque entité :
            <!-- BEGIN level2 level3 -->
            <div class="statement-new-league-rule">
              <!-- END -->
              <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
                <li><var>x</var> : Position X (<const>0</const> commence à gauche)</li>
                <li><var>y</var> : Position Y (<const>0</const> commence en haut)</li>
                <li><var>type</var> : 
                  <!-- BEGIN level4 -->
                  <div class="statement-new-league-rule">
                    <!-- END -->
                    <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
                      <li><const>WALL</const> pour un mur</li>
                      <li><const>ROOT</const> pour un organe de type ROOT</li>
                      <li><const>BASIC</const> pour un organe de type BASIC</li>
                      <!-- BEGIN level2 level3 level4 -->
                      <li><const>HARVESTER</const> pour un organe de type HARVESTER</li>
                      <!-- END -->
                      <!-- BEGIN level3 level4 -->
                      <li><const>TENTACLE</const> pour un organe de type TENTACLE</li>
                      <!-- END -->
                      <!-- BEGIN level4 -->
                      <li><const>SPORER</const> pour un organe de type SPORER</li>
                      <!-- END -->
                      <li><const>A</const> pour une source de protéine A</li>
                      <!-- BEGIN level4 -->
                      <li><const>B</const> pour une source de protéine B</li>
                      <li><const>C</const> pour une source de protéine C</li>
                      <li><const>D</const> pour une source de protéine D</li>
                      <!-- END -->
                    </ul>
                    <!-- BEGIN level4 -->
                  </div>
                  <!-- END -->
                  
                </li>
                <li><var>owner</var> :
                  <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
                    <li><const>1</const> si vous êtes le propriétaire de cet organe</li>
                    <li><const>0</const> si votre adversaire est le propriétaire de cet organe</li>
                    <li><const>-1</const> si cette entité n'est pas un organe</li>
                  </ul>
                </li>
                <li><var>organId</var> : id unique de cette entité si c'est un organe, <const>0</const> sinon.</li>
                <!-- BEGIN level1 -->
                <li><var>organDir</var> : <const>N</const>, <const>W</const>, <const>S</const>, ou <const>E</const>, non utilisé dans cette ligue</li>
                <!-- END -->
                <!-- BEGIN level2 level3 level4 -->
                <li><var>organDir</var> : <const>N</const>, <const>W</const>, <const>S</const>, ou <const>E</const> pour la direction vers laquelle cet organe fait face</li>
                <!-- END -->
                <li><var>organParentId</var> : si c'est un organe, l'<var>organId</var> de l'organe dont cet organe est issu (0 pour les organes <const>ROOT</const>), <const>0</const> sinon.</li>
                <li><var>organRootId</var> : si c'est un organe, l'<var>organId</var> de l'organe <const>ROOT</const> ancêtre de cet organe, <const>0</const> sinon.</li>
              </ul>
              <!-- BEGIN level2 level3 -->
            </div>
            <!-- END -->
            <span class="statement-lineno">Prochaine ligne :</span> <const>4</const> entiers : <var>myA</var>,<var>myB</var>,<var>myC</var>,<var>myD</var> pour les quantités de chaque protéine que vous possédez.
            <br/>
            <span class="statement-lineno">Prochaine ligne :</span> <const>4</const> entiers : <var>oppA</var>,<var>oppB</var>,<var>oppC</var>,<var>oppD</var> pour les quantités de chaque protéine que votre adversaire possède.
            <br/>
            <!-- BEGIN level1 level2 level3 -->
            <span class="statement-lineno">Prochaine ligne :</span> un entier <var>requiredActionsCount</var> égal à 
            
            <const>1</const> <em>pour cette ligue</em>.
            <!-- END -->
            <!-- BEGIN level4 -->
            <span class="statement-lineno">Prochaine ligne :</span> un entier <var>requiredActionsCount</var> égal au nombre de commandes que vous avez à entrer pour ce tour.
            <!-- END -->
          </div>
        </div>
        <!-- Protocol block -->
        <div class="blk">
          <div class="title">Sortie</div>
          <div class="text">
            Une ligne par organisme avec son action :
            
            <ul style="padding-left: 20px;padding-top: 0">
              <li>
                <!-- BEGIN level1 -->
                <action>GROW id x y type</action> : tenter de faire pousser un nouvel organe de type <var>type</var> à la position <var>x</var>, <var>y</var> depuis l'organe <var>id</var>. Si la position cible n'est pas voisine de <var>id</var>, l'organe sera créé sur le plus court chemin vers <var>x</var>, <var>y</var>.
                <!-- END -->
                <!-- BEGIN level2 level3 level4 -->
                <action>GROW id x y type direction</action> : tenter de faire pousser un nouvel organe de type <var>type</var> à la position <var>x</var>, <var>y</var> depuis l'organe <var>id</var>. Si la position cible n'est pas voisine de <var>id</var>, l'organe sera créé sur le plus court chemin vers <var>x</var>, <var>y</var>.
                <!-- END -->
              </li>
              <!-- BEGIN level4 -->
              <li>
                <action>SPORE id x y</action> : tenter de créer un nouvel organe <const>ROOT</const> à la position <var>x</var>, <var>y</var> depuis le <const>SPORER</const> <var>id</var>.
              </li>
              <!-- END -->
              <li>
                <action>WAIT</action> : ne rien faire.
              </li>
            </ul>
            Ajoutez du texte après votre commande et celui-ci sera affiché sur le viewer.
          </div>
        </div>
        <div class="blk">
          <div class="title">Contraintes</div>
          <div class="text">
            Temps de réponse par tour ≤ <const>50</const>ms
            <br>Temps de réponse pour le premier tour ≤ <const>1000</const>ms
          </div>
        </div>
        <!-- BEGIN level1 -->
      </details>
      <!-- END -->
      <!-- BEGIN level2 level3 level4 -->
    </details>
    <!-- END -->
    
    <!-- BEGIN level1 level2 level3 -->
    <!-- LEAGUE ALERT -->
    <div style="color: #7cc576; 
    background-color: rgba(124, 197, 118,.1);
    padding: 20px;
    
    margin-top: 10px;
    text-align: left;">
    <div style="text-align: center; margin-bottom: 6px"><img
      src="//cdn.codingame.com/smash-the-code/statement/league_wood_04.png" /></div>
      
      <p style="text-align: center; font-weight: 700; margin-bottom: 6px;">Qu'est-ce qui m'attend dans les ligues suivantes ?
      </p>
      Les règles supplémentaires disponibles dans les ligues supérieures seront les suivantes:<ul>
        <!-- BEGIN level1 -->
        <li>Un type d'organe pour rassembler plus de protéines</li>
        <!-- END -->
        <!-- BEGIN level1 level2 -->
        <li>Un type d'organe pour attaquer votre adversaire</li>
        <!-- END -->
        <!-- BEGIN level1 level2 level3 -->
        <li>Un type d'organe pour engendrer d'autres organismes</li>
        <!-- END -->
      </ul>
    </div>
    <!-- END -->
    



            <!-- STORY -->
    <div class="statement-story-background">
        <div class="statement-story-cover"
            style="background-size: cover; background-image: url(/servlet/fileservlet?id=131085121432944)">
            <div class="statement-story" style="min-height: 300px; position: relative">
                <h2><span style="color: #b3b9ad">Pour Démarrer</span></h2>
                <div class="story-text">
                    Pourquoi ne pas se lancer dans la bataille avec l'un de ces <b>IA Starters</b>, fournis par
                    l'équipe&nbsp;:
                          <ul>
        <!--
        <li>C++
          <a style="color: #f2bb13; border-bottom: 1px dotted #f2bb13;"
          rel="nofollow" target="_blank" href="https://gist.github.com/CGjupoulton/4e2f1e2182ac35fa84d211a28bedd55b">https://gist.github.com/CGjupoulton/4e2f1e2182ac35fa84d211a28bedd55b</a>
        </li>
        -->
        <li>JavaScript
          <a style="color: #f2bb13; border-bottom: 1px dotted #f2bb13;"
          rel="nofollow" target="_blank" href="https://gist.github.com/CGjupoulton/8c9f5b64a5d4967402b53a0bb526e167">https://gist.github.com/CGjupoulton/8c9f5b64a5d4967402b53a0bb526e167</a>
        </li>
        <li>Java
          <a style="color: #f2bb13; border-bottom: 1px dotted #f2bb13;"
          rel="nofollow" target="_blank" href="https://gist.github.com/CGjupoulton/6bfad6a5e62d61bdfe36a593f21833a4">https://gist.github.com/CGjupoulton/6bfad6a5e62d61bdfe36a593f21833a4</a>
        </li>
        <li>Python
          <a style="color: #f2bb13; border-bottom: 1px dotted #f2bb13;"
          rel="nofollow" target="_blank" href="https://gist.github.com/CGjupoulton/9b15eca86001975297e6a1290a301dd1">https://gist.github.com/CGjupoulton/9b15eca86001975297e6a1290a301dd1</a>
        </li>
        <li>TypeScript
          <a style="color: #f2bb13; border-bottom: 1px dotted #f2bb13;"
          rel="nofollow" target="_blank" href="https://gist.github.com/CGjupoulton/76039cf5cccb9811a04f83c2f14bced6">https://gist.github.com/CGjupoulton/76039cf5cccb9811a04f83c2f14bced6</a>
        </li>
      </ul>
                    <p>
                        Vous pouvez les modifier selon votre style, ou les prendre comme exemple pour tout coder à
                        partir de
                        zero.
                    </p>
                </div>
            </div>
        </div>
    </div>

  </div>
  <!-- END -->
  
  <!-- BEGIN level5 -->
  <div id="statement_back" class="statement_back" style="display: none"></div>
  <div class="statement-body">
    
    <!-- GOAL -->
    <div class="statement-section statement-goal">
      <h2>
        <span class="icon icon-goal">&nbsp;</span>
        <span>Objectif</span>
      </h2>
      <div class="statement-goal-content">
        
        
        
        <div>
          Faites grandir votre organisme pour qu'il devienne le plus grand !
        </div>
        
        <div style="text-align: center; margin: 15px">
          
          <img src="https://static.codingame.com/servlet/fileservlet?id=132396041223454"
          alt="Grow your organism to become the largest!" style="width: 60%; max-width: 300px" />
          
          
        </div>
        
      </div>
    </div>
    <!-- RULES -->
    <div class="statement-section statement-rules">
      <h2>
        <span class="icon icon-rules">&nbsp;</span>
        <span>Règles</span>
      </h2>
      
      <div class="statement-rules-content">
        <p>Le jeu se déroule sur une grille.<br><br>
          
        </p>
        <br>
        
        <h3 style="font-size: 14px;
        font-weight: 700;
        padding-top: 5px;
        padding-bottom: 15px;">
        🔵🔴 Les Organismes</h3>
        
        <p>Les <b>Organismes</b> sont composés d'<b>organes</b> occupant <const>une</const> case d'espace sur la grille de jeu.</p>
        
        <br>
        <p>Chaque joueur commence avec un organe de type <var>ROOT</var>. Votre organisme peut faire pousser (<action>GROW</action>) un nouvel organe à chaque tour afin de couvrir une plus large surface.</p>
        
        <br/>
        <p>Un nouvel organisme peut pousser <b>depuis</b> n'importe quel <b>organe</b> existant, vers un <b>emplacement adjacent libre</b>.</p>
        <br>
        
        <p> Afin d'utiliser l'action <action>GROW</action>, votre organisme a besoin de <b>protéines</b>. Faire pousser 1 organe <var>BASIC</var> nécessite <const>1</const> protéine de type A.
        </p>
        <br/>
        <p>
          Vous pouvez obtenir plus de <b>protéines</b> en faisant pousser un organe sur une case de la grille contenant une <b>source de protéine</b> ; celles-ci sont des cases avec une lettre à l'intérieur. Faire ceci vous octroiera <const>3</const> protéines du type correspondant.
        </p>
        <br>
        
        <p>
          <b>Faites pousser plus d'organes que le Boss pour progresser vers la prochaine ligue.</b>
        </p>
        <br>
        
        <p>Votre organisme peut recevoir les commandes suivantes:</p>
        
        <ul>
          <li>
            <action>GROW id x y type</action>: créé un nouvel organe à la position <var>x</var>, <var>y</var> depuis un organe ayant l'id <var>id</var>. Si la position cible n'est pas voisine de <var>id</var>, l'organe sera créé sur le plus court chemin vers <var>x</var>, <var>y</var>.
            
            <div style="text-align: center; margin: 15px">
              <img src="https://static.codingame.com/servlet/fileservlet?id=132395721182727"
              style="width: 400px; max-width: 100%" />
              <div style="margin: auto; width: 400px; max-width: 100%"><em>Cette commande va créer un nouvel organe <var>BASIC</var> depuis l'organe <var>ROOT</var> parent.</em></div>
            </div>
          </li>
          
          
        </ul>
        <br>
        
        <p>Voir la section <b>Protocole de jeu</b> pour plus d'informations sur l'envoi de commandes à votre organisme.</p>
        <br>
        
        <!-- harvester -->
        <div style="margin-top: 30px">
          <h2>
            <span class="icon icon-rules">&nbsp;</span>
            <span>Règles du HARVESTER</span>
          </h2>
          
          
          <div style="text-align: center; margin: 15px">
            <img src="https://static.codingame.com/servlet/fileservlet?id=132395760074979"
            style="width: 400px; max-width: 100%" />
            <div style="margin: auto; width: 400px; max-width: 100%"><em>Cette commande crééra un nouveau <action>HARVESTER</action> faisant face à <var>N</var> (Nord).</em></div>
          </div>
          
          <p>Si un <action>HARVESTER</action> fait face à une case avec une <b>source de protéines</b>, vous recevrez <const>1</const> de cette protéine à <b>chaque fin de tour</b>.</p>
          <br>
          <p><em>Note : chaque joueur gagne seulement <const>1</const> protéine par source par tour, même si plusieurs <action>HARVESTER</action> sont dirigés vers cette source.</em></p>
          <br>
          <p>Pour faire pousser un <action>HARVESTER</action>, vous avez besoin de <const>1</const> protéine de type <var>C</var> et <const>1</const> protéine de type <var>D</var>.</p>
          
          
        </div>
        
        <!-- tentacl -->
        <div style="margin-top: 30px">
          <h2>
            <span class="icon icon-rules">&nbsp;</span>
            <span>Règles du TENTACLE</span>
          </h2>
          
          <div class="statement-rules-content">
            À chaque tour, juste après la phase de <b>récolte</b>, chaque organe <action>TENTACLE</action> faisant face à un organe adverse l'<b>attaquera</b>, causant la <b>mort</b> de l'organe adverse. Les attaques se produisent simultanément.
          </div>
          
          <div style="text-align: center; margin: 15px">
            <img src="https://static.codingame.com/servlet/fileservlet?id=132395781400673"
            style="width: 400px; max-width: 100%" />
            <div style="margin: auto; width: 400px; max-width: 100%"><em>Cette commande crééra un nouveau <action>TENTACLE</action> faisant face à <var>E</var> (Est), menant à l'attaque de l'organe adverse.</em></div>
          </div>
          
          
          <p>Quand un organe <b>meurt,</b> tout ses <b>enfants</b> meurent également. Cela se propagera à <b>tout</b> l'organisme si le <action>ROOT</action> est ainsi détruit.</p>
          <br>
          
          <p><em>Note: Vous pouvez utiliser la variable <var>organParentId</var> pour recenser les enfants de chaque organe.</em></p>
          <br>
          
          <p>Un tentacule empêche également l'adversaire de faire pousser un organe sur la case en face de celui-ci.</p>
          <br>
          
          <p>Pour faire pousser un <action>TENTACLE</action> vous avez besoin de <const>1</const> protéine de type <var>B</var> et <const>1</const> protéine de type <var>C</var>.</p>
          <br>
        </p>
        
        
      </div>
      
      <!--sporer-->
      <div style="margin-top: 30px">
        <h2>
          <span class="icon icon-rules">&nbsp;</span>
          <span>Règles du SPORER</span>
        </h2>
        
        <div class="statement-rules-content">
          <p>
            L'organe  de type <action>SPORER</action> est unique de deux manières :
            <ul>
              <li>Il est le seul organe pouvant créer un nouvel organe <action>ROOT</action>.</li>
              <li>Pour créer un nouveau <action>ROOT</action>, il projette une spore en ligne droite, vous permettant de placer le nouvel organe <action>ROOT</action> sur n'importe quelle case libre lui faisant face.</li>
            </ul>
          </p>
          
          <p><em>Note: un organe <action>ROOT</action> n'a jamais de <b>parent</b>, même s'il a été créé depuis un <action>SPORER</action>.</em></p>
          <br>
          
          
          <div style="text-align: center; margin: 15px">
            <img src="https://static.codingame.com/servlet/fileservlet?id=132395742195955"
            style="width: 400px; max-width: 100%" />
            <div style="margin: auto; width: 400px; max-width: 100%"><em>Cette commande permettra au <action>SPORER</action> de créer un nouveau <action>ROOT</action> vers le Sud.</em></div>
          </div>
          
          
          <p>Lorsque vous contrôlez <b>plusieurs</b> organismes, vous devez envoyer une commande pour <b>chacun d'eux</b>. Ils effectueront leurs actions de manière simultanée.</p>
          <br>
          
          <p>La variable <var>requiredActionsCount</var> représente le nombre d'organismes que vous contrôlez. Vous <b>devez</b> utiliser la commande <action>WAIT</action> pour chaque organisme qui ne peut agir.</p>
          <br>
          
          <p><em>Note : Vous pouvez utiliser la variable <var>organRootId</var> pour déterminer quels organes appartiennent au même organisme.</em></p>
          <br>
          
          <p>Pour faire pousser un <action>SPORER</action> vous avez besoin de <const>1</const> protéine de type <var>B</var> et <const>1</const> protéine de type <var>D</var>.</p>
          <p>Pour produire un nouveau <action>ROOT</action> vous avez besoin de <const>1</const> protéine de chaque type.</p>
          <br>
          
          <p>Voici une table résumant les coûts des différents organes :</p>
          <table style="margin-bottom: 20px">
            <thead>
              <tr>
                <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">Organe</th>
                <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">A</th>
                <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">B</th>
                <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">C</th>
                <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">D</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style="padding: 5px;outline: 1px solid #838891;"><action>BASIC</action></td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
                <td style="padding: 5px;outline: 1px solid #838891;">0</td>
                <td style="padding: 5px;outline: 1px solid #838891;">0</td>
                <td style="padding: 5px;outline: 1px solid #838891;">0</td>
              </tr>
              <tr>
                <td style="padding: 5px;outline: 1px solid #838891;"><action>HARVESTER</action></td>
                <td style="padding: 5px;outline: 1px solid #838891;">0</td>
                <td style="padding: 5px;outline: 1px solid #838891;">0</td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
              </tr>
              <tr>
                <td style="padding: 5px;outline: 1px solid #838891;"><action>TENTACLE</action></td>
                <td style="padding: 5px;outline: 1px solid #838891;">0</td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
                <td style="padding: 5px;outline: 1px solid #838891;">0</td>
              </tr>
              <tr>
                <td style="padding: 5px;outline: 1px solid #838891;"><action>SPORER</action></td>
                <td style="padding: 5px;outline: 1px solid #838891;">0</td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
                <td style="padding: 5px;outline: 1px solid #838891;">0</td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
              </tr>
              <tr>
                <td style="padding: 5px;outline: 1px solid #838891;"><action>ROOT</action></td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
                <td style="padding: 5px;outline: 1px solid #838891;">1</td>
              </tr>
            </tbody>
          </table>
          
          
          
          
          
        </div>
      </div>
      
      
      <br>
      <h3 style="font-size: 14px;
      font-weight: 700;
      padding-top: 5px;
      padding-bottom: 15px;">
      ⛔ Fin du jeu</h3>
      
      <p>
        Le jeu se termine quand il détecte qu'aucun progrès ne peut plus être fait ou après <const>100</const> tours.<br>
        <br>
      </p>
      
      <h3 style="font-size: 16px;
      font-weight: 700;
      padding-top: 20px;
      color: #838891;
      padding-bottom: 15px;">
      🎬 Ordre des actions pour un tour</h3>
      
      <ol>
        <li>
          Les actions <action>GROW</action> et <action>SPORE</action> sont calculées.
        </li>
        <li>
          Les murs issus de collisions sont générés.
        </li>
        <li>
          Les récoltes de protéines sont calculées.
        </li>
        <li>
          Les attaques de tentacules sont calculées.
        </li>
        <li>
          Les conditions de fin de partie sont vérifiées.
        </li>
      </ol>
      
      <br>
      
      
      <!-- Victory conditions -->
      <div class="statement-victory-conditions">
        <div class="icon victory"></div>
        <div class="blk">
          <div class="title">Conditions de victoire</div>
          <div class="text">
            <ul style="padding-top:0; padding-bottom: 0;">
              Le gagnant est le joueur ayant le plus de cases occupées par un de ses organes.
            </ul>
          </div>
        </div>
      </div>
      <!-- Lose conditions -->
      <div class="statement-lose-conditions">
        <div class="icon lose"></div>
        <div class="blk">
          <div class="title">Conditions de défaite</div>
          <div class="text">
            <ul style="padding-top:0; padding-bottom: 0;">
              Votre programme ne fournit pas une commande dans le temps imparti ou fournit une commande non reconnue.
            </ul>
          </div>
        </div>
      </div>
      <br>
      <h3 style="font-size: 14px;
      font-weight: 700;
      padding-top: 5px;
      padding-bottom: 15px;">
      🐞 Conseils de débogage</h3>
      <ul>
        <li>Survolez la grille pour voir plus d'informations sur les organes sous votre curseur.</li>
        <li>Ajoutez du texte à la fin d'une instruction pour afficher ce texte au dessus de votre organisme.</li>
        <li>Cliquez sur la roue dentée pour afficher les options visuelles supplémentaires.</li>
        <li>Utilisez le clavier pour contrôler l'action : espace pour play / pause, les flèches pour avancer pas à pas.</li>
      </ul>
    </div>
  </div>
  
  
  <!-- PROTOCOL -->
  <div class="statement-section statement-protocol">
    <h2 style="font-size: 20px;">
      <span class="icon icon-protocol">&nbsp;</span>
      <span>Protocole de jeu</span>
    </h2>
    <!-- Protocol block -->
    <div class="blk">
      <div class="title">Entrées d'Initialisation</div>
      <div class="text">
        <span class="statement-lineno">Première ligne :</span> deux entiers <var>width</var> et <var>height</var> pour la taille de la grille.<br>
      </div>
    </div>
    <!-- Protocol block -->
    <div class="blk">
      <div class="title">Entrées pour un tour de jeu</div>
      <div class="text">
        <span class="statement-lineno">Première ligne :</span> un entier <var>entityCount</var> pour le nombre d'entités sur la grille.<br>
        <span class="statement-lineno">Prochaines <var>entityCount</var> lignes :</span> Les <const>7</const> entrées suivantes pour chaque entité :
        <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
          <li><var>x</var> : Position X (<const>0</const> commence à gauche)</li>
          <li><var>y</var> : Position Y (<const>0</const> commence en haut)</li>
          <li><var>type</var> : 
            <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
              <li><const>WALL</const> pour un mur</li>
              <li><const>ROOT</const> pour un organe de type ROOT</li>
              <li><const>BASIC</const> pour un organe de type BASIC</li>
              <li><const>HARVESTER</const> pour un organe de type HARVESTER</li>
              <li><const>TENTACLE</const> pour un organe de type TENTACLE</li>
              <li><const>SPORER</const> pour un organe de type SPORER</li>
              <li><const>A</const> pour une source de protéine A</li>
              <li><const>B</const> pour une source de protéine B</li>
              <li><const>C</const> pour une source de protéine C</li>
              <li><const>D</const> pour une source de protéine D</li>
            </ul>
          </li>
          <li><var>owner</var> :
            <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
              <li><const>1</const> si vous êtes le propriétaire de cet organe</li>
              <li><const>0</const> si votre adversaire est le propriétaire de cet organe</li>
              <li><const>-1</const> si cette entité n'est pas un organe</li>
            </ul>
          </li>
          <li><var>organId</var> : id unique de cette entité si c'est un organe, <const>0</const> sinon.</li>
          <li><var>organDir</var> : <const>N</const>, <const>W</const>, <const>S</const>, ou <const>E</const> pour la direction vers laquelle cet organe fait face</li>
          <li><var>organParentId</var> : si c'est un organe, l'<var>organId</var> de l'organe dont cet organe est issu (0 pour les organes <const>ROOT</const>), <const>0</const> sinon.</li>
          <li><var>organRootId</var> : si c'est un organe, l'<var>organId</var> de l'organe <const>ROOT</const> ancêtre de cet organe, <const>0</const> sinon.</li>
        </ul>
        <span class="statement-lineno">Prochaine ligne :</span> <const>4</const> entiers : <var>myA</var>,<var>myB</var>,<var>myC</var>,<var>myD</var> pour les quantités de chaque protéine que vous possédez.
        <br/>
        <span class="statement-lineno">Prochaine ligne :</span> <const>4</const> entiers : <var>oppA</var>,<var>oppB</var>,<var>oppC</var>,<var>oppD</var> pour les quantités de chaque protéine que votre adversaire possède.
        <br/>
        <span class="statement-lineno">Prochaine ligne :</span> un entier <var>requiredActionsCount</var> égal au nombre de commandes que vous avez à entrer pour ce tour.
      </div>
    </div>
    <!-- Protocol block -->
    <div class="blk">
      <div class="title">Sortie</div>
      <div class="text">
        <!-- BEGIN level1 level2 level3 -->
        Une seule ligne avec votre action :
        <!-- END -->
        <!-- BEGIN level4 -->
        Une ligne par organisme avec son action :
        <!-- END -->
        
        <ul style="padding-left: 20px;padding-top: 0">
          <li>
            <action>GROW id x y type direction</action> : tenter de faire pousser un nouvel organe de type <var>type</var> à la position <var>x</var>, <var>y</var> depuis l'organe <var>id</var>. Si la position cible n'est pas voisine de <var>id</var>, l'organe sera créé sur le plus court chemin vers <var>x</var>, <var>y</var>.
          </li>
          <li>
            <action>SPORE id x y</action> : tenter de créer un nouvel organe <const>ROOT</const> à la position <var>x</var>, <var>y</var> depuis le <const>SPORER</const> <var>id</var>.
          </li>
          <li>
            <action>WAIT</action> : ne rien faire.
          </li>
        </ul>
        Ajoutez du texte après votre commande et celui-ci sera affiché sur le viewer.
      </div>
    </div>
    <div class="blk">
      <div class="title">Contraintes</div>
      <div class="text">
        Temps de réponse par tour ≤ <const>50</const>ms
        <br>Temps de réponse pour le premier tour ≤ <const>1000</const>ms
      <br><const>16</const> &le; <var>width</var> &le; <const>24</const>
      <br><const>8</const> &le; <var>height</var> &le; <const>12</const>
      </div>
    </div>
  </div>
</div>
<!-- SHOW_SAVE_PDF_BUTTON -->
<!-- END -->