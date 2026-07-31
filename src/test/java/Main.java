import java.util.Properties;

import com.codingame.gameengine.runner.MultiplayerGameRunner;

public class Main {
    public static void main(String[] args) {

        MultiplayerGameRunner gameRunner = new MultiplayerGameRunner();

        // Set seed here (leave empty for random)
        gameRunner.setSeed(7700970175115819776l);
        gameRunner.setLeagueLevel(5);

        // Select agents here
        gameRunner.addAgent("python3 config/Boss.py", "Boss");
        gameRunner.addAgent("python3 config/Boss.py", "Boss");

        Properties params = new Properties();
        // Set params here
        gameRunner.setGameParameters(params);

        gameRunner.start(8888);
    }
}
