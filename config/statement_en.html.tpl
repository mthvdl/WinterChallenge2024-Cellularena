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
    This is a <b>league based</b> challenge.
  </p>
  <span class="statement-league-alert-content">
    For this challenge, multiple leagues for the same game are available. Once you have proven your skills against the
    first Boss, you will access a higher league and extra rules will be available.
    <br><br>
    <b>NEW:</b> In low leagues, your submission will only fight the boss in the arena. Win a best-of-five to advance.
  </span>
</div>

<!-- BEGIN level4 -->
<div class="statement-section statement-goal">
  <h2>
    <span class="icon icon-goal">&nbsp;</span>
    <span>Congratulations</span>
  </h2>
  <div class="statement-goal-content">
    
    <p>
      Your organism can <b>fight</b>!
    </p>
    
    <p>
      However, your organism has been <b>alone</b> so far. But with the power of a <action>SPORER</action> type organ, you can grow entirely <b>new organisms</b>.
    </p>
    
    <div style="text-align: center; margin: 15px">
      
      <img src="https://static.codingame.com/servlet/fileservlet?id=132396021519497"/>
      <div style="margin: auto; width: 400px; max-width: 100%"><em>The SPORER organ.</em></div>
    </div>
  </div>
</div>

<div class="statement-section statement-rules">
  <h2>
    <span class="icon icon-rules">&nbsp;</span>
    <span>SPORER Rules</span>
  </h2>
  
  <div class="statement-rules-content">
    <p>
      The <action>SPORER</action> type organ is unique in two ways:
      <ul>
        <li>It is the only organ that can create a new <action>ROOT</action> organ.</li>
        <li>To create a new <action>ROOT</action>, it shoots out a spore in a straight line, letting you place the new organ in any of the free spaces it is facing.</li>
      </ul>
    </p>
    
    <p><em>Note: a <action>ROOT</action> organ never has a <b>parent</b>, even when spawned from a <action>SPORER</action>.</em></p>
    <br>
    
    
    <div style="text-align: center; margin: 15px">
      <img src="https://static.codingame.com/servlet/fileservlet?id=132395742195955"
      style="width: 400px; max-width: 100%" />
      <div style="margin: auto; width: 400px; max-width: 100%"><em>This command will make the <action>SPORER</action> shoot a new <action>ROOT</action> to the South.</em></div>
    </div>
    
    
    <p>When you control <b>multiple</b> organisms, you must output one command for <b>each one</b>. They will perform their actions simultaneously.</p>
    <br>
    
    <p>The <var>requiredActionsCount</var> variable will keep track of how many organisms you have. You <b>must</b> use the <action>WAIT</action> command for any organism that cannot act.</p>
    <br>
    
    <p><em>Note: You can use the <var>organRootId</var> variable to find out which organs belong to the same organism.</em></p>
    <br>
    
    <p>To grow a <action>SPORER</action> you need <const>1</const> <var>B</var> type protein and <const>1</const> <var>D</var> type protein.</p>
    <p>To spore a new <action>ROOT</action> you need <const>1</const> of each protein.</p>
    <br>
    
    <p>Here is a table to summarize all organ costs:</p>
    <table style="margin-bottom: 20px">
      <thead>
        <tr>
          <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">Organ</th>
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
    <p> In this league, there is <b>one</b> protein source but your starting organism is not close enough to <b>harvest it</b>.
    </p>
    <!-- END -->
    <p>
      <b>Use a sporer to shoot a new <action>ROOT</action> towards the protein and grow larger than your opponent!</b></p>
      
      <!-- BEGIN level4 -->
      <br>
      <p><em>New information added to the <b>Game Protocol</b> section.</em></p>
      <!-- END -->
    </div>
  </div>
  <!-- END -->
  
  <!-- BEGIN level3 -->
  <div class="statement-section statement-goal">
    <h2>
      <span class="icon icon-goal">&nbsp;</span>
      <span>Congratulations</span>
    </h2>
    <div class="statement-goal-content">
      
      <p>
        Your organism can <b>harvest</b>!
      </p>
      
      <p>
        However, <b>your opponent</b> will sometimes be <b>in your way</b>. Give them a taste of your <action>TENTACLE</action> type organ.
      </p>
      
      <div style="text-align: center; margin: 15px">
        
        <img src="https://static.codingame.com/servlet/fileservlet?id=132395883395976"/>
        <div style="margin: auto; width: 400px; max-width: 100%"><em>The TENTACLE organ.</em></div>
      </div>
    </div>
  </div>
  
  <!-- END -->
  
  <!-- BEGIN level3 level4 -->
  <div class="statement-section statement-rules">
    <h2>
      <span class="icon icon-rules">&nbsp;</span>
      <span>TENTACLE Rules</span>
    </h2>
    
    <div class="statement-rules-content">
      On each turn, right after <b>harvesting</b>, any <action>TENTACLE</action> organs facing an opponent organ will <b>attack</b>, causing the target organ to <b>die</b>. Attacks happen simultaneously.
    </div>
    
    <div style="text-align: center; margin: 15px">
      <img src="https://static.codingame.com/servlet/fileservlet?id=132395781400673"
      style="width: 400px; max-width: 100%" />
      <div style="margin: auto; width: 400px; max-width: 100%"><em>This command will create a new <action>TENTACLE</action> facing <var>E</var> (East), causing the opponent organ to be attacked.</em></div>
    </div>
    
    
    <p>When an organ <b>dies,</b> all of its <b>children</b> also die. This will propagate to the <b>entire</b> organism if the <action>ROOT</action> is hit.</p>
    <br>
    
    <p><em>Note: You can use the <var>organParentId</var> variable to keep track of each organ's children.</em></p>
    <br>
    
    <p>A tentacle also prevents the opponent from growing onto the tile it is facing.</p>
    <br>
    
    <p>To grow a <action>TENTACLE</action> you need <const>1</const> <var>B</var> type protein and <const>1</const> <var>C</var> type protein.</p>
    <br>
    <!-- BEGIN level3 -->
    <p> In this league, there are no <b>protein sources</b> but you start with a stock full of various proteins.
      <br>
      <!-- END -->
      <b>Use them to grow a large organism and attack the opponent's organism!</b></p>
      
      <!-- BEGIN level3 -->
      <br>
      <p><em>New information added to the <b>Game Protocol</b> section.</em></p>
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
          Your organism can <b>grow</b>!
        </p>
        
        <p>
          However, <b>protein sources</b> on the grid are limited, and once you absorb them, they are gone. This is where the <action>HARVESTER</action> type organ comes in.
        </p>
        
        <div style="text-align: center; margin: 15px">
          
          <img src="https://static.codingame.com/servlet/fileservlet?id=132395829688056"/>
          <div style="margin: auto; width: 400px; max-width: 100%"><em>The HARVESTER organ.</em></div>
        </div>
      </div>
    </div>
    <!-- END -->
    <!-- BEGIN level2 level3 level4 -->
    <div class="statement-section statement-rules">
      <h2>
        <span class="icon icon-rules">&nbsp;</span>
        <span>HARVESTER Rules</span>
      </h2>
      
      <!-- BEGIN level2 -->
      <div class="statement-rules-content">
        From this league onwards, organs you place may be given a <var>direction</var>.
      </div>
      <!-- END -->
      
      <div style="text-align: center; margin: 15px">
        <img src="https://static.codingame.com/servlet/fileservlet?id=132395760074979"
        style="width: 400px; max-width: 100%" />
        <div style="margin: auto; width: 400px; max-width: 100%"><em>This command will create new <action>HARVESTER</action> facing <var>N</var> (North).</em></div>
      </div>
      
      <p>If a <action>HARVESTER</action> is facing a tile with a <b>protein source</b>, you will receive <const>1</const> of that protein on <b>every end of turn</b>.</p>
      <br>
      <p><em>Note: each player gains only <const>1</const> protein from each source per turn, even if multiple harvesters are facing that source.</em></p>
      <br>
      <p>To grow a <action>HARVESTER</action> you need <const>1</const> <var>C</var> type protein and <const>1</const> <var>D</var> type protein.</p>
      <!-- BEGIN level2 -->
      <br>
      <p> In this league, you are given an extra <const>1</const> <var>C</var> type protein and <const>1</const> <var>D</var> type protein, <b>use them to grow a harvester at the correct location to grow your organism indefinitely!</b></p>
      <!-- END -->
      
      <!-- BEGIN level2 -->
      <br>
      <p><em>New information added to the <b>Game Protocol</b> section.</em></p>
      <!-- END -->
      
    </div>
    <!-- END -->
    
    <!-- GOAL -->
    <!-- BEGIN level1 -->
    <div class="statement-section statement-goal">
      <h2>
        <span class="icon icon-goal">&nbsp;</span>
        <span>Goal</span>
      </h2>
      <div class="statement-goal-content">
        
        
        
        <div>
          Grow your organism to become the largest!
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
        <span>Rules</span>
      </h2>
      
      <div class="statement-rules-content">
        <p>The game is played on a grid.<br><br>
          
          For the lower leagues, you need only beat the Boss in specific situations.
          
        </p>
        <br>
        
        <h3 style="font-size: 14px;
        font-weight: 700;
        padding-top: 5px;
        padding-bottom: 15px;">
        🔵🔴 The Organisms</h3>
        
        <p><b>Organisms</b> are made up of <b>organs</b> that take up <const>one</const> tile of space on the game grid.</p>
        
        <br>
        <!-- BEGIN level1 -->
        <p>Each player starts with a <var>ROOT</var> type organ. In this league, your organism can <action>GROW</action> a new <var>BASIC</var> type organ on each turn in order to cover a larger area.</p>
        <!-- END -->
        <!-- BEGIN level2 level3 level4 -->
        <p>Each player starts with a <var>ROOT</var> type organ. Your organism can <action>GROW</action> a new organ on each turn in order to cover a larger area.</p>
        <!-- END -->
        
        <br/>
        <p>A new organ can grow <b>from</b> any existing <b>organ</b>, onto an <b>empty adjacent location</b>.</p>
        <br>
        
        <!-- BEGIN level1 -->
        <p> In order to <action>GROW</action>, your organism needs <b>proteins</b>.</p>
        <p>    In this league, you start with <const>10</const> proteins of type <var>A</var>. Growing 1 <var>BASIC</var> organ requires <const>1</const> of these proteins.
        </p>
        <!-- END -->
        <!-- BEGIN level2 level3 level4 -->
        <p> In order to <action>GROW</action>, your organism needs <b>proteins</b>. Growing 1 <var>BASIC</var> organ requires <const>1</const> protein of type A.
        </p>
        <!-- END -->
        <br/>
        <p>
          You can obtain more <b>proteins</b> by growing an organ onto a tile of the grid containing a <b>protein source</b>, these are tiles with a letter in them. Doing so will grant you <const>3</const> proteins of the corresponding type.
        </p>
        <br>
        
        <p>
          <b>Grow more organs than the Boss to advance to the next league.</b>
        </p>
        <br>
        
        <p>You organism can receive the following command:</p>
        
        <ul>
          <li>
            <action>GROW id x y type</action>: creates a new organ at location <var>x</var>, <var>y</var> from organ with id <var>id</var>. If the target location is not a neighbour of <var>id</var>, the organ will be created on the shortest path to <var>x</var>, <var>y</var>.
            
            <div style="text-align: center; margin: 15px">
              <img src="https://static.codingame.com/servlet/fileservlet?id=132395721182727"
              style="width: 400px; max-width: 100%" />
              <div style="margin: auto; width: 400px; max-width: 100%"><em>This command will create new <var>BASIC</var> organ with the <var>ROOT</var> organ as its parent.</em></div>
            </div>
          </li>
          
          
        </ul>
        <br>
        
        <p>See the <b>Game Protocol</b> section for more information on sending commands to your organism.</p>
        <br>
        
        <br>
        <h3 style="font-size: 14px;
        font-weight: 700;
        padding-top: 5px;
        padding-bottom: 15px;">
        ⛔ Game end</h3>
        
        <p>
          The game stops when it detects progress can no longer be made or after <const>100</const> turns.<br>
          <br>
        </p>
        
        <!-- Victory conditions -->
        <div class="statement-victory-conditions">
          <div class="icon victory"></div>
          <div class="blk">
            <div class="title">Victory Conditions</div>
            <div class="text">
              <ul style="padding-top:0; padding-bottom: 0;">
                The winner is the player with the most tiles occupied by one of their organs.
              </ul>
            </div>
          </div>
        </div>
        <!-- Lose conditions -->
        <div class="statement-lose-conditions">
          <div class="icon lose"></div>
          <div class="blk">
            <div class="title">Defeat Conditions</div>
            <div class="text">
              <ul style="padding-top:0; padding-bottom: 0;">
                Your program does not provide a command in the alloted time or one of the commands is invalid.
              </ul>
            </div>
          </div>
        </div>
        <br>
        <h3 style="font-size: 14px;
        font-weight: 700;
        padding-top: 5px;
        padding-bottom: 15px;">
        🐞 Debugging tips</h3>
        <ul>
          <li>Hover over the grid to see extra information on the organ under your mouse.</li>
          <li>Append text after any command and that text will appear above your organism.</li>
          <li>Press the gear icon on the viewer to access extra display options.</li>
          <li>Use the keyboard to control the action: space to play/pause, arrows to step 1 frame at a time.</li>
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
        
        <span style="display: inline-block; margin-bottom: 10px;">Click to expand</span>
        <h2 style="margin-bottom: 0;">
          <span class="icon icon-protocol">&nbsp;</span>
          <span>Game Protocol</span>
        </h2>
      </summary>
      <!-- Protocol block -->
      <div class="blk">
        <div class="title">Initialization Input</div>
        <div class="text">
          <span class="statement-lineno">First line:</span> two integers <var>width</var> and <var>height</var> for the size
          of the grid.<br>
        </div>
      </div>
      <!-- Protocol block -->
      <div class="blk">
        <div class="title">Input for One Game Turn</div>
        <div class="text">
          <span class="statement-lineno">First line:</span> one integer <var>entityCount</var> for the number of entities on the grid.<br>
          <span class="statement-lineno">Next <var>entityCount</var> lines:</span> the following <const>7</const> inputs for each entity:
          <!-- BEGIN level2 level3 -->
          <div class="statement-new-league-rule">
            <!-- END -->
            <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
              <li><var>x</var>: X coordinate (<const>0</const> is leftmost)</li>
              <li><var>y</var>: Y coordinate (<const>0</const> is topmost)</li>
              <li><var>type</var>: 
                <!-- BEGIN level4 -->
                <div class="statement-new-league-rule">
                  <!-- END -->
                  <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
                    <li><const>WALL</const> for a wall</li>
                    <li><const>ROOT</const> for a ROOT type organ</li>
                    <li><const>BASIC</const> for a BASIC type organ</li>
                    <!-- BEGIN level2 level3 level4 -->
                    <li><const>HARVESTER</const> for a HARVESTER type organ</li>
                    <!-- END -->
                    <!-- BEGIN level3 level4 -->
                    <li><const>TENTACLE</const> for a TENTACLE type organ</li>
                    <!-- END -->
                    <!-- BEGIN level4 -->
                    <li><const>SPORER</const> for a SPORER type organ</li>
                    <!-- END -->
                    <li><const>A</const> for an A protein source</li>
                    <!-- BEGIN level4 -->
                    <li><const>B</const> for a B protein source</li>
                    <li><const>C</const> for a C protein source</li>
                    <li><const>D</const> for a D protein source</li>
                    <!-- END -->
                  </ul>
                  <!-- BEGIN level4 -->
                </div>
                <!-- END -->
                
              </li>
              <li><var>owner</var>:
                <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
                  <li><const>1</const> if you are the owner of this organ</li>
                  <li><const>0</const> if your opponent owns this organ</li>
                  <li><const>-1</const> if this is not an organ</li>
                </ul>
              </li>
              <li><var>organId</var>: unique id of this entity if it is an organ, <const>0</const> otherwise</li>
              <!-- BEGIN level1 -->
              <li><var>organDir</var>: <const>N</const>, <const>W</const>, <const>S</const>, or <const>E</const>, not used in this league</li>
              <!-- END -->
              <!-- BEGIN level2 level3 level4 -->
              <li><var>organDir</var>: <const>N</const>, <const>W</const>, <const>S</const>, or <const>E</const> for the direction in which this organ is facing</li>
              <!-- END -->
              <li><var>organParentId</var>: if it is an organ, the <var>organId</var> of the organ that this organ grew from (0 for <const>ROOT</const> organs), else <const>0</const>.</li>
              <li><var>organRootId</var>: if it is an organ, the <var>organId</var> of the <const>ROOT</const> that this organ originally grew from, else <const>0</const>.</li>
            </ul>
            <!-- BEGIN level2 level3 -->
          </div>
          <!-- END -->
          <span class="statement-lineno">Next line:</span> <const>4</const> integers: <var>myA</var>,<var>myB</var>,<var>myC</var>,<var>myD</var> for the amount of each protein type you have.
          <br/>
          <span class="statement-lineno">Next line:</span> <const>4</const> integers: <var>oppA</var>,<var>oppB</var>,<var>oppC</var>,<var>oppD</var> for the amount of each protein type your opponent has.
          <br/>
          <!-- BEGIN level1 level2 level3 -->
          <span class="statement-lineno">Next line:</span> the integer <var>requiredActionsCount</var> which equals 
          
          <const>1</const> <em>in this league</em>.
          <!-- END -->
          <!-- BEGIN level4 -->
          <span class="statement-lineno">Next line:</span> the integer <var>requiredActionsCount</var> which equals the number of command you have to perform during the turn.
          <!-- END -->
        </div>
      </div>
      <!-- Protocol block -->
      <div class="blk">
        <div class="title">Output</div>
        <div class="text">
          <!-- BEGIN level1 level2 level3 -->
          A single line with your action:
          <!-->
          <!-- BEGIN level4 -->
          A single line per organism with its action:
          <!-->
          
          <ul style="padding-left: 20px;padding-top: 0">
            <li>
              <!-- BEGIN level1 -->
              <action>GROW id x y type</action> : attempt to grow a new organ of type <var>type</var> at location <var>x</var>, <var>y</var> from organ with id <var>id</var>. If the target location is not a neighbour of <var>id</var>, the organ will be created on the shortest path to <var>x</var>, <var>y</var>.
              <!-- END -->
              <!-- BEGIN level2 level3 level4 -->
              <action>GROW id x y type direction</action> : attempt to grow a new organ of type <var>type</var> at location <var>x</var>, <var>y</var> from organ with id <var>id</var>. If the target location is not a neighbour of <var>id</var>, the organ will be created on the shortest path to <var>x</var>, <var>y</var>.
              <!-- END -->
            </li>
            <!-- BEGIN level4 -->
            <li>
              <action>SPORE id x y</action> : attempt to create a new <const>ROOT</const> organ at location <var>x</var>, <var>y</var> from the <const>SPORER</const> with id <var>id</var>.
            </li>
            <!-- END -->
            <li>
              <action>WAIT</action> : do nothing.
            </li>
          </ul>
          Append text to your command and it will be displayed in the viewer.
        </div>
      </div>
      <div class="blk">
        <div class="title">Constraints</div>
        <div class="text">
          Response time per turn ≤ <const>50</const>ms
          <br>Response time for the first turn ≤ <const>1000</const>ms
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
    
    <p style="text-align: center; font-weight: 700; margin-bottom: 6px;">What is in store for me in the higher leagues?
    </p>
    The extra rules available in higher leagues are:<ul>
      <!-- BEGIN level1 -->
      <li>An organ type to gather more proteins</li>
      <!-- END -->
      <!-- BEGIN level1 level2 -->
      <li>An organ type to attack your opponent</li>
      <!-- END -->
      <!-- BEGIN level1 level2 level3 -->
      <li>An organ type to spawn more organisms</li>
      <!-- END -->
    </ul>
  </div>
  <!-- END -->
  <!-- STORY -->
<div class="statement-story-background">
  <div class="statement-story-cover"
  style="background-size: cover; background-image: url(/servlet/fileservlet?id=131085121432944)">
  <div class="statement-story" style="min-height: 300px; position: relative">
    <h2><span style="color: #b3b9ad">To Start</span></h2>
    <div class="story-text">
      Why not start the battle with one of these <b>IA Starters</b>, provided by the team:
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
        You can modify them to match your style or take them as an example to code everything from
        scratch.
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
      <span>Goal</span>
    </h2>
    <div class="statement-goal-content">
      
      
      
      <div>
        Grow your organism to become the largest!
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
      <span>Rules</span>
    </h2>
    
    <div class="statement-rules-content">
      <p>The game is played on a grid.<br><br>
        
      </p>
      <br>
      
      <h3 style="font-size: 14px;
      font-weight: 700;
      padding-top: 5px;
      padding-bottom: 15px;">
      🔵🔴 The Organisms</h3>
      
      <p><b>Organisms</b> are made up of <b>organs</b> that take up <const>one</const> tile of space on the game grid.</p>
      
      <br>
      
      <p>Each player starts with a <var>ROOT</var> type organ. Your organism can <action>GROW</action> a new organ on each turn in order to cover a larger area.</p>
      
      
      <br/>
      <p>A new organ can grow <b>from</b> any existing <b>organ</b>, onto an <b>empty adjacent location</b>.</p>
      <br>
      
      
      
      <p> In order to <action>GROW</action>, your organism needs <b>proteins</b>. Growing 1 <var>BASIC</var> organ requires <const>1</const> protein of type A.
      </p>
      
      <br/>
      <p>
        You can obtain more <b>proteins</b> by growing an organ onto a tile of the grid containing a <b>protein source</b>, these are tiles with a letter in them. Doing so will grant you <const>3</const> proteins of the corresponding type.
      </p>
      <br>
      
      
      <br>
      
      <p>You organism can receive the following command:</p>
      
      <ul>
        <li>
          <action>GROW id x y type</action>: creates a new organ at location <var>x</var>, <var>y</var> from organ with id <var>id</var>. If the target location is not a neighbour of <var>id</var>, the organ will be created on the shortest path to <var>x</var>, <var>y</var>.
          
          <div style="text-align: center; margin: 15px">
            <img src="https://static.codingame.com/servlet/fileservlet?id=132395721182727"
            style="width: 400px; max-width: 100%" />
            <div style="margin: auto; width: 400px; max-width: 100%"><em>This command will create new <var>BASIC</var> organ with the <var>ROOT</var> organ as its parent.</em></div>
          </div>
        </li>
        
        
      </ul>
      <br>
      
      <p>See the <b>Game Protocol</b> section for more information on sending commands to your organism.</p>
      <br>
      
      <!-- harvester -->
      <div style="margin-top: 30px;">
        <h2>
          <span class="icon icon-rules">&nbsp;</span>
          <span>HARVESTER Rules</span>
        </h2>
        
        <div class="statement-rules-content">
          Organs you place may be given a <var>direction</var>.
        </div>
        
        <div style="text-align: center; margin: 15px">
          <img src="https://static.codingame.com/servlet/fileservlet?id=132395760074979"
          style="width: 400px; max-width: 100%" />
          <div style="margin: auto; width: 400px; max-width: 100%"><em>This command will create new <action>HARVESTER</action> facing <var>N</var> (North).</em></div>
        </div>
        
        <p>If a <action>HARVESTER</action> is facing a tile with a <b>protein source</b>, you will receive <const>1</const> of that protein on <b>every end of turn</b>.</p>
        <br>
        <p><em>Note: each player gains only <const>1</const> protein from each source per turn, even if multiple harvesters are facing that source.</em></p>
        <br>
        <p>To grow a <action>HARVESTER</action> you need <const>1</const> <var>C</var> type protein and <const>1</const> <var>D</var> type protein.</p>
        
      </div>
      
      
      
      
      <!-- tentac -->
      <div style="margin-top: 30px;">
        <h2>
          <span class="icon icon-rules">&nbsp;</span>
          <span>TENTACLE Rules</span>
        </h2>
        
        <div class="statement-rules-content">
          On each turn, right after <b>harvesting</b>, any <action>TENTACLE</action> organs facing an opponent organ will <b>attack</b>, causing the target organ to <b>die</b>. Attacks happen simultaneously.
        </div>
        
        <div style="text-align: center; margin: 15px">
          <img src="https://static.codingame.com/servlet/fileservlet?id=132395781400673"
          style="width: 400px; max-width: 100%" />
          <div style="margin: auto; width: 400px; max-width: 100%"><em>This command will create a new <action>TENTACLE</action> facing <var>E</var> (East), causing the opponent organ to be attacked.</em></div>
        </div>
        
        
        <p>When an organ <b>dies,</b> all of its <b>children</b> also die. This will propagate to the <b>entire</b> organism if the <action>ROOT</action> is hit.</p>
        <br>
        
        <p><em>Note: You can use the <var>organParentId</var> variable to keep track of each organ's children.</em></p>
        <br>
        
        <p>A tentacle also prevents the opponent from growing onto the tile it is facing.</p>
        <br>
        
        <p>To grow a <action>TENTACLE</action> you need <const>1</const> <var>B</var> type protein and <const>1</const> <var>C</var> type protein.</p>
        <br>
        
        
      </p>
      
    </div>
    
    <!-- sporer -->
    <div style="margin-top: 30px;">
      <h2>
        <span class="icon icon-rules">&nbsp;</span>
        <span>SPORER Rules</span>
      </h2>
      
      <div class="statement-rules-content">
        <p>
          The <action>SPORER</action> type organ is unique in two ways:
          <ul>
            <li>It is the only organ that can create a new <action>ROOT</action> organ.</li>
            <li>To create a new <action>ROOT</action>, it shoots out a spore in a straight line, letting you place the new organ in any of the free spaces it is facing.</li>
          </ul>
        </p>
        
        <p><em>Note: a <action>ROOT</action> organ never has a <b>parent</b>, even when spawned from a <action>SPORER</action>.</em></p>
        <br>
        
        
        <div style="text-align: center; margin: 15px">
          <img src="https://static.codingame.com/servlet/fileservlet?id=132395742195955"
          style="width: 400px; max-width: 100%" />
          <div style="margin: auto; width: 400px; max-width: 100%"><em>This command will make the <action>SPORER</action> shoot a new <action>ROOT</action> to the South.</em></div>
        </div>
        
        
        <p>When you control <b>multiple</b> organisms, you must output one command for <b>each one</b>. They will perform their actions simultaneously.</p>
        <br>
        
        <p>The <var>requiredActionsCount</var> variable will keep track of how many organisms you have. You <b>must</b> use the <action>WAIT</action> command for any organism that cannot act.</p>
        <br>
        
        <p><em>Note: You can use the <var>organRootId</var> variable to find out which organs belong to the same organism.</em></p>
        <br>
        
        <p>To grow a <action>SPORER</action> you need <const>1</const> <var>B</var> type protein and <const>1</const> <var>D</var> type protein.</p>
        <p>To spore a new <action>ROOT</action> you need <const>1</const> of each protein.</p>
        <br>
        
        <p>Here is a table to summarize all organ costs:</p>
        <table style="margin-bottom: 20px">
          <thead>
            <tr>
              <th style="text-align: center; padding: 5px; outline: 1px solid #838891;">Organ</th>
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
    ⛔ Game end</h3>
    
    <p>
      The game stops when it detects progress can no longer be made or after <const>100</const> turns.<br>
      <br>
    </p>
    
    <h3 style="font-size: 16px;
    font-weight: 700;
    padding-top: 20px;
    color: #838891;
    padding-bottom: 15px;">
    🎬 Action order for one turn</h3>
    
    
    <ol>
      <li>
        <action>GROW</action> and <action>SPORE</action> actions are computed.
      </li>
      <li>
        Extra walls from growth collisions are spawned.
      </li>
      <li>
        Protein harvests are computed.
      </li>
      <li>
        Tentacle attacks are computed.
      </li>
      <li>
        Game over conditions are checked.
      </li>
    </ol>
    
    <br>
    
    
    <!-- Victory conditions -->
    <div class="statement-victory-conditions">
      <div class="icon victory"></div>
      <div class="blk">
        <div class="title">Victory Conditions</div>
        <div class="text">
          <ul style="padding-top:0; padding-bottom: 0;">
            The winner is the player with the most tiles occupied by one of their organs.
          </ul>
        </div>
      </div>
    </div>
    <!-- Lose conditions -->
    <div class="statement-lose-conditions">
      <div class="icon lose"></div>
      <div class="blk">
        <div class="title">Defeat Conditions</div>
        <div class="text">
          <ul style="padding-top:0; padding-bottom: 0;">
            Your program does not provide a command in the alloted time or one of the commands is invalid.
          </ul>
        </div>
      </div>
    </div>
    <br>
    <h3 style="font-size: 14px;
    font-weight: 700;
    padding-top: 5px;
    padding-bottom: 15px;">
    🐞 Debugging tips</h3>
    <ul>
      <li>Hover over the grid to see extra information on the organ under your mouse.</li>
      <li>Append text after any command and that text will appear above your organism.</li>
      <li>Press the gear icon on the viewer to access extra display options.</li>
      <li>Use the keyboard to control the action: space to play/pause, arrows to step 1 frame at a time.</li>
    </ul>
  </div>
</div>


<!-- PROTOCOL -->

<div  class="statement-section statement-protocol">
  
  <h2 style="font-size: 20px;">
    <span class="icon icon-protocol">&nbsp;</span>
    <span>Game Protocol</span>
  </h2>
  
  <!-- Protocol block -->
  <div class="blk">
    <div class="title">Initialization Input</div>
    <div class="text">
      <span class="statement-lineno">First line:</span> two integers <var>width</var> and <var>height</var> for the size
      of the grid.<br>
    </div>
  </div>
  <!-- Protocol block -->
  <div class="blk">
    <div class="title">Input for One Game Turn</div>
    <div class="text">
      <span class="statement-lineno">First line:</span> one integer <var>entityCount</var> for the number of entities on the grid.<br>
      <span class="statement-lineno">Next <var>entityCount</var> lines:</span> the following <const>7</const> inputs for each entity:
      
      <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
        <li><var>x</var>: X coordinate (<const>0</const> is leftmost)</li>
        <li><var>y</var>: Y coordinate (<const>0</const> is topmost)</li>
        <li><var>type</var>: 
          
          <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
            <li><const>WALL</const> for a wall</li>
            <li><const>ROOT</const> for a ROOT type organ</li>
            <li><const>BASIC</const> for a BASIC type organ</li>
            
            <li><const>HARVESTER</const> for a HARVESTER type organ</li>
            
            
            <li><const>TENTACLE</const> for a TENTACLE type organ</li>
            
            
            <li><const>SPORER</const> for a SPORER type organ</li>
            
            <li><const>A</const> for an A protein source</li>
            
            <li><const>B</const> for a B protein source</li>
            <li><const>C</const> for a C protein source</li>
            <li><const>D</const> for a D protein source</li>
            
          </ul>
          
        </div>
        
        
      </li>
      <li><var>owner</var>:
        <ul style="padding-left: 20px;padding-top:0;padding-bottom:0px">
          <li><const>1</const> if you are the owner of this organ</li>
          <li><const>0</const> if your opponent owns this organ</li>
          <li><const>-1</const> if this is not an organ</li>
        </ul>
      </li>
      <li><var>organId</var>: unique id of this entity if it is an organ, <const>0</const> otherwise</li>
      <li><var>organDir</var>: <const>N</const>, <const>W</const>, <const>S</const>, or <const>E</const> for the direction in which this organ is facing</li>
      <li><var>organParentId</var>: if it is an organ, the <var>organId</var> of the organ that this organ grew from (0 for <const>ROOT</const> organs), else <const>0</const>.</li>
      <li><var>organRootId</var>: if it is an organ, the <var>organId</var> of the <const>ROOT</const> that this organ originally grew from, else <const>0</const>.</li>
    </ul>
    
    <span class="statement-lineno">Next line:</span> <const>4</const> integers: <var>myA</var>,<var>myB</var>,<var>myC</var>,<var>myD</var> for the amount of each protein type you have.
    <br/>
    <span class="statement-lineno">Next line:</span> <const>4</const> integers: <var>oppA</var>,<var>oppB</var>,<var>oppC</var>,<var>oppD</var> for the amount of each protein type your opponent has.
    <br/>
    <span class="statement-lineno">Next line:</span> the integer <var>requiredActionsCount</var> which equals the number of command you have to perform during the turn.
  </div>
  
  <!-- Protocol block -->
  <div class="blk">
    <div class="title">Output</div>
    <div class="text">
      A single line per organism with its action:
      
      <ul style="padding-left: 20px;padding-top: 0">
        <li>
          <action>GROW id x y type direction</action> : attempt to grow a new organ of type <var>type</var> at location <var>x</var>, <var>y</var> from organ with id <var>id</var>. If the target location is not a neighbour of <var>id</var>, the organ will be created on the shortest path to <var>x</var>, <var>y</var>.
        </li>
        
        <li>
          <action>SPORE id x y</action> : attempt to create a new <const>ROOT</const> organ at location <var>x</var>, <var>y</var> from the <const>SPORER</const> with id <var>id</var>.
        </li>
        
        <li>
          <action>WAIT</action> : do nothing.
        </li>
      </ul>
      Append text to your command and it will be displayed in the viewer.
    </div>
  </div>
  
  <div class="blk">
    <div class="title">Constraints</div>
    <div class="text">
      Response time per turn ≤ <const>50</const>ms
      <br>Response time for the first turn ≤ <const>1000</const>ms
      <br><const>16</const> &le; <var>width</var> &le; <const>24</const>
      <br><const>8</const> &le; <var>height</var> &le; <const>12</const>
       
    </div>
  </div>
  
</div>

<!-- SHOW_SAVE_PDF_BUTTON -->
<!-- END -->




