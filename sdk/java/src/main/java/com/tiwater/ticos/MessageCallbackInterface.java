package com.tiwater.ticos;

import org.json.JSONObject;

/**
 * Interface for handling incoming messages.
 */
public interface MessageCallbackInterface {
    /**
     * Handle an incoming message.
     * 
     * @param message The message to handle
     * @return true if the message was handled successfully
     */
    boolean handleMessage(JSONObject message);
}
