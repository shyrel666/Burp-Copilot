package com.burpai.core;

import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.proxy.http.InterceptedResponse;
import burp.api.montoya.proxy.http.ProxyResponseHandler;
import burp.api.montoya.proxy.http.ProxyResponseReceivedAction;
import burp.api.montoya.proxy.http.ProxyResponseToBeSentAction;

/**
 * Listens to proxy responses and forwards in-scope request/response pairs to the
 * {@link AutoAnalysisEngine}. Always continues the response unchanged so proxy
 * processing is never blocked or altered.
 */
public final class AutoAnalysisProxyListener implements ProxyResponseHandler {
    private final AutoAnalysisEngine engine;

    public AutoAnalysisProxyListener(AutoAnalysisEngine engine) {
        this.engine = engine;
    }

    @Override
    public ProxyResponseReceivedAction handleResponseReceived(InterceptedResponse interceptedResponse) {
        try {
            HttpRequest request = interceptedResponse.initiatingRequest();
            if (request != null) {
                String url;
                try {
                    url = request.url();
                } catch (RuntimeException ex) {
                    url = null;
                }
                if (url != null) {
                    engine.onProxyResponse(
                            url,
                            request.toString(),
                            interceptedResponse.toString(),
                            interceptedResponse.annotations());
                }
            }
        } catch (RuntimeException ignored) {
            // never let auto-analysis interfere with proxying
        }
        return ProxyResponseReceivedAction.continueWith(interceptedResponse);
    }

    @Override
    public ProxyResponseToBeSentAction handleResponseToBeSent(InterceptedResponse interceptedResponse) {
        return ProxyResponseToBeSentAction.continueWith(interceptedResponse);
    }
}
