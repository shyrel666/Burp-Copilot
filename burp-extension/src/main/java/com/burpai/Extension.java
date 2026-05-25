package com.burpai;

import burp.api.montoya.BurpExtension;
import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.ui.contextmenu.ContextMenuEvent;
import burp.api.montoya.ui.contextmenu.ContextMenuItemsProvider;
import com.burpai.core.AnalysisRequestBuilder;
import com.burpai.core.AnalysisResultFormatter;
import com.burpai.core.BackendClient;
import com.burpai.core.HttpMessageFilter;
import com.burpai.core.PreparedHttpMessage;

import javax.swing.JButton;
import javax.swing.JLabel;
import javax.swing.JMenuItem;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.JTextField;
import javax.swing.SwingUtilities;
import javax.swing.SwingWorker;
import java.awt.BorderLayout;
import java.awt.Component;
import java.awt.GridLayout;
import java.util.ArrayList;
import java.util.List;

public class Extension implements BurpExtension, ContextMenuItemsProvider {
    private MontoyaApi api;
    private JTextField backendUrlField;
    private JTextField tokenField;
    private JTextArea resultArea;

    @Override
    public void initialize(MontoyaApi api) {
        this.api = api;
        api.extension().setName("AI HTTP Analyzer");
        api.userInterface().registerSuiteTab("AI Analyzer", createPanel());
        api.userInterface().registerContextMenuItemsProvider(this);
        api.logging().logToOutput("AI HTTP Analyzer loaded.");
    }

    @Override
    public List<Component> provideMenuItems(ContextMenuEvent event) {
        List<Component> items = new ArrayList<>();
        if (event.selectedRequestResponses().isEmpty()) {
            return items;
        }
        JMenuItem analyze = new JMenuItem("AI Analyze");
        analyze.addActionListener(ignored -> submitSelected(event, "analyze"));
        JMenuItem learn = new JMenuItem("AI Learn Mode");
        learn.addActionListener(ignored -> submitSelected(event, "learn"));
        items.add(analyze);
        items.add(learn);
        return items;
    }

    private JPanel createPanel() {
        JPanel panel = new JPanel(new BorderLayout());
        JPanel settings = new JPanel(new GridLayout(3, 2));
        backendUrlField = new JTextField("http://localhost:8000");
        tokenField = new JTextField("");
        JButton healthButton = new JButton("Test Backend");
        healthButton.addActionListener(ignored -> testBackend());
        settings.add(new JLabel("Backend URL"));
        settings.add(backendUrlField);
        settings.add(new JLabel("Backend Token"));
        settings.add(tokenField);
        settings.add(new JLabel(""));
        settings.add(healthButton);

        resultArea = new JTextArea();
        resultArea.setEditable(false);
        resultArea.setLineWrap(true);
        resultArea.setWrapStyleWord(true);
        panel.add(settings, BorderLayout.NORTH);
        panel.add(new JScrollPane(resultArea), BorderLayout.CENTER);
        return panel;
    }

    private void submitSelected(ContextMenuEvent event, String mode) {
        HttpRequestResponse selected = event.selectedRequestResponses().get(0);
        String request = selected.request().toString();
        String response = selected.response() == null ? null : selected.response().toString();
        String targetUrl = selected.request().url();
        PreparedHttpMessage prepared = HttpMessageFilter.prepare(request, response, targetUrl);
        String json = AnalysisRequestBuilder.build("burp", mode, prepared);
        runInBackground("Analyzing selected traffic...", () -> {
            BackendClient client = new BackendClient(backendUrlField.getText(), tokenField.getText());
            return client.analyze(json);
        });
    }

    private void testBackend() {
        runInBackground("Testing backend connection...", () -> {
            BackendClient client = new BackendClient(backendUrlField.getText(), tokenField.getText());
            return client.health() ? "Backend health check succeeded." : "Backend health check failed.";
        });
    }

    private void runInBackground(String loadingMessage, BackendTask task) {
        setResult(loadingMessage);
        new SwingWorker<String, Void>() {
            @Override
            protected String doInBackground() throws Exception {
                return task.run();
            }

            @Override
            protected void done() {
                try {
                    setResult(AnalysisResultFormatter.forDisplay(get()));
                } catch (Exception exc) {
                    setResult("Backend request failed: " + exc.getMessage());
                    api.logging().logToError("AI Analyzer backend request failed", exc);
                }
            }
        }.execute();
    }

    private void setResult(String text) {
        SwingUtilities.invokeLater(() -> resultArea.setText(text));
    }

    private interface BackendTask {
        String run() throws Exception;
    }
}
