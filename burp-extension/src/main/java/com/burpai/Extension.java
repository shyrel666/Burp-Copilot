package com.burpai;

import burp.api.montoya.BurpExtension;
import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.http.message.responses.HttpResponse;
import burp.api.montoya.ui.contextmenu.ContextMenuEvent;
import burp.api.montoya.ui.contextmenu.ContextMenuItemsProvider;
import burp.api.montoya.ui.contextmenu.MessageEditorHttpRequestResponse;
import com.burpai.core.AnalysisRequestBuilder;
import com.burpai.core.AnalysisResultFormatter;
import com.burpai.core.BackendClient;
import com.burpai.core.HttpMessageFilter;
import com.burpai.core.PreparedHttpMessage;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
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
import java.awt.Dimension;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

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
        if (!hasSelectedMessage(event)) {
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
        backendUrlField = new JTextField("http://localhost:8000");
        tokenField = new JTextField("");
        JButton healthButton = new JButton("Test Backend");
        healthButton.addActionListener(ignored -> testBackend());

        JPanel settings = new JPanel();
        settings.setLayout(new BoxLayout(settings, BoxLayout.Y_AXIS));
        settings.setBorder(BorderFactory.createEmptyBorder(8, 8, 8, 8));
        settings.add(labeledRow("Backend URL", backendUrlField));
        settings.add(Box.createVerticalStrut(4));
        settings.add(labeledRow("Backend Token", tokenField));
        settings.add(Box.createVerticalStrut(4));
        JPanel buttonRow = new JPanel(new BorderLayout());
        buttonRow.add(healthButton, BorderLayout.EAST);
        buttonRow.setMaximumSize(new Dimension(Integer.MAX_VALUE, healthButton.getPreferredSize().height + 4));
        settings.add(buttonRow);

        resultArea = new JTextArea();
        resultArea.setEditable(false);
        resultArea.setLineWrap(true);
        resultArea.setWrapStyleWord(true);
        panel.add(settings, BorderLayout.NORTH);
        panel.add(new JScrollPane(resultArea), BorderLayout.CENTER);
        return panel;
    }

    private static JPanel labeledRow(String labelText, JTextField field) {
        JPanel row = new JPanel(new BorderLayout(8, 0));
        JLabel label = new JLabel(labelText);
        label.setPreferredSize(new Dimension(120, label.getPreferredSize().height));
        row.add(label, BorderLayout.WEST);
        row.add(field, BorderLayout.CENTER);
        row.setMaximumSize(new Dimension(Integer.MAX_VALUE, field.getPreferredSize().height + 4));
        return row;
    }

    private void submitSelected(ContextMenuEvent event, String mode) {
        SelectedMessage message = extractMessage(event);
        if (message == null) {
            setResult("No request was available from this context.");
            return;
        }
        String request = message.request.toString();
        String response = message.response == null ? null : message.response.toString();
        String targetUrl = message.targetUrl;
        PreparedHttpMessage prepared = HttpMessageFilter.prepare(request, response, targetUrl);
        String json = AnalysisRequestBuilder.build("burp", mode, prepared);
        runInBackground("Analyzing selected traffic...", () -> {
            BackendClient client = new BackendClient(backendUrlField.getText(), tokenField.getText());
            return client.analyze(json);
        });
    }

    private static boolean hasSelectedMessage(ContextMenuEvent event) {
        if (!event.selectedRequestResponses().isEmpty()) {
            return true;
        }
        Optional<MessageEditorHttpRequestResponse> editor = event.messageEditorRequestResponse();
        return editor.isPresent() && editor.get().requestResponse().request() != null;
    }

    private static SelectedMessage extractMessage(ContextMenuEvent event) {
        if (!event.selectedRequestResponses().isEmpty()) {
            HttpRequestResponse selected = event.selectedRequestResponses().get(0);
            return new SelectedMessage(selected.request(), selected.response(), selected.request().url());
        }
        Optional<MessageEditorHttpRequestResponse> editor = event.messageEditorRequestResponse();
        if (editor.isPresent()) {
            HttpRequestResponse rr = editor.get().requestResponse();
            HttpRequest request = rr.request();
            if (request == null) {
                return null;
            }
            HttpResponse response = rr.response();
            return new SelectedMessage(request, response, request.url());
        }
        return null;
    }

    private static final class SelectedMessage {
        final HttpRequest request;
        final HttpResponse response;
        final String targetUrl;

        SelectedMessage(HttpRequest request, HttpResponse response, String targetUrl) {
            this.request = request;
            this.response = response;
            this.targetUrl = targetUrl;
        }
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
