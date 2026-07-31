package com.codingame.game;

import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.codingame.game.action.Action;
import com.codingame.game.action.ActionType;
import com.codingame.gameengine.core.GameManager;
import com.codingame.gameengine.core.MultiplayerGameManager;
import com.google.inject.Inject;
import com.google.inject.Singleton;

@Singleton
public class CommandManager {

    @Inject private MultiplayerGameManager<Player> gameManager;

    public void handleCommands(Player player, List<String> lines) {

        for (String command : lines) {
            try {
                Matcher match;

                boolean found = false;
                try {
                    for (ActionType actionType : ActionType.values()) {
                        match = actionType.getPattern().matcher(command.trim());
                        if (match.matches()) {
                            Action action = new Action(actionType);
                            actionType.getConsumer().accept(match, action);
                            player.addAction(action);
                            found = true;
                            break;
                        }
                    }
                } catch (Exception e) {
                    throw new InvalidInputException(Game.getExpected(command), e.toString());
                }

                if (!found) {
                    throw new InvalidInputException(Game.getExpected(command), command);
                }

            } catch (InvalidInputException e) {
                deactivatePlayer(player, e.getMessage());
                gameManager.addToGameSummary(e.getMessage());
                gameManager.addToGameSummary(GameManager.formatErrorMessage(player.getNicknameToken() + ": disqualified!"));
            }
        }

    }

    private void deactivatePlayer(Player player, String message) {
        player.deactivate(escapeHTMLEntities(message));
    }

    private String escapeHTMLEntities(String message) {
        return message
            .replace("&lt;", "<")
            .replace("&gt;", ">");
    }

    private void matchMessage(Player agent, Matcher match) {
        String message = match.group("message");
        if (message != null) {
            agent.setMessage(message);
        }
    }
}
