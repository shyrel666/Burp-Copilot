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
import com.burpai.core.BackendErrorMessage;
import com.burpai.core.ExtensionSettings;
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
import javax.swing.Timer;
import java.awt.BorderLayout;
import java.awt.Component;
import java.awt.Dimension;
import java.awt.Font;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.CancellationException;
import java.util.concurrent.InterruptedException;

public class Extension implements BurpExtension, ContextMenuItemsProvider {
    private MontoyaApi api;
    private ExtensionSettings settings;
    private JTextField backendUrlField;
    private JTextField tokenField;
    private JTextArea resultArea;
    private JButton cancelButton;
    private JLabel statusLabel;
    private SwingWorker<String, Void> activeWorker;
    private Timer elapsedTimer;
    private int elapsedSeconds;

    @Override
    public void initialize(MontoyaApi api) {
        this.api = api;
        this.settings = new ExtensionSettings(api);
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
        JMenuItem analyze = new JMenuItem("AI Analyze (request + response)");
        analyze.addActionListener(ignored -> submitSelected(event, "analyze"));
        JMenuItem learn = new JMenuItem("AI Learn Mode (request + response)");
        learn.addActionListener(ignored -> submitSelected(event, "learn"));
        items.add(analyze);
        items.add(learn);
        return items;
    }

    private JPanel createPanel() {
        JPanel panel = new JPanel(new BorderLayout());

        backendUrlField = new JTextField(settings.getBackendUrl());
        tokenField = new JTextField(settings.getBackendToken());

        JButton healthButton = new JButton("Test Backend");
        healthButton.addActionListener(ignored -> testBackend());
        JButton saveButton = new JButton("Save Settings");
        saveButton.addActionListener(ignored -> saveSettings());

        JPanel settingsPanel = new JPanel();
        settingsPanel.setLayout(new BoxLayout(settingsPanel, BoxLayout.Y_AXIS));
        settingsPanel.setBorder(BorderFactory.createEmptyBorder(8, 8, 8, 8));
        settingsPanel.add(labeledRow("Backend URL", backendUrlField));
        settingsPanel.add(Box.createVerticalStrut(4));
        settingsPanel.add(labeledRow("Backend Token", tokenField));
        settingsPanel.add(Box.createVerticalStrut(4));
        JPanel buttonRow = new JPanel(new BorderLayout(8, 0));
        JPanel leftButtons = new JPanel();
        leftButtons.add(saveButton);
        buttonRow.add(leftButtons, BorderLayout.WEST);
        buttonRow.add(healthButton, BorderLayout.EAST);
        buttonRow.setMaximumSize(new Dimension(Integer.MAX_VALUE, healthButton.getPreferredSize().height + 4));
        settingsPanel.add(buttonRow);

        resultArea = new JTextArea();
        resultArea.setEditable(false);
        resultArea.setLineWrap(true);
        resultArea.setWrapStyleWord(true);
        resultArea.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 13));

        statusLabel = new JLabel("Ready");
        statusLabel.setBorder(BorderFactory.createEmptyBorder(2, 4, 2, 4));

        cancelButton = new JButton("Cancel");
        cancelButton.setEnabled(false);
        cancelButton.addActionListener(ignored -> cancelActiveWorker());
        JPanel statusRow = new JPanel(new BorderLayout(4, 0));
        statusRow.add(statusLabel, BorderLayout.CENTER);
        statusRow.add(cancelButton, BorderLayout.EAST);

        panel.add(settingsPanel, BorderLayout.NORTH);
        panel.add(new JScrollPane(resultArea), BorderLayout.CENTER);
        panel.add(statusRow, BorderLayout.SOUTH);
        return panel;
    }

    private void saveSettings() {
        settings.setBackendUrl(backendUrlField.getText());
        settings.setBackendToken(tokenField.getText());
        setResult("Settings saved. They will persist across Burp restarts.");
        api.logging().logToOutput("Extension settings saved.");
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
        String loadingMessage = response == null
                ? "Analyzing selected request..."
                : "Analyzing selected request and response...";
        runInBackground(loadingMessage, () -> {
            BackendClient client = new BackendClient(backendUrlField.getText(), tokenField.getText());
            return client.analyze(json);
        });
    }

    private static boolean hasSelectedMessage(ContextMenuEvent event) {
        Optional<MessageEditorHttpRequestResponse> editor = event.messageEditorRequestResponse();
        if (editor.isPresent() && editor.get().requestResponse().request() != null) {
            return true;
        }
        return !event.selectedRequestResponses().isEmpty();
    }

    private static SelectedMessage extractMessage(ContextMenuEvent event) {
        Optional<MessageEditorHttpRequestResponse> editor = event.messageEditorRequestResponse();
        if (editor.isPresent()) {
            SelectedMessage message = selectedMessageFrom(editor.get().requestResponse());
            if (message != null) {
                return message;
            }
        }
        if (!event.selectedRequestResponses().isEmpty()) {
            return selectedMessageFrom(event.selectedRequestResponses().get(0));
        }
        return null;
    }

    private static SelectedMessage selectedMessageFrom(HttpRequestResponse rr) {
        HttpRequest request = rr.request();
        if (request == null) {
            return null;
        }
        HttpResponse response = rr.response();
        return new SelectedMessage(request, response, request.url());
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
        cancelActiveWorker();
        setResult(loadingMessage);
        statusLabel.setText(loadingMessage);
        cancelButton.setEnabled(true);
        elapsedSeconds = 0;
        startElapsedTimer();

        SwingWorker<String, Void> worker = new SwingWorker<String, Void>() {
            @Override
            protected String doInBackground() throws Exception {
                return task.run();
            }

            @Override
            protected void done() {
                stopElapsedTimer();
                cancelButton.setEnabled(false);
                try {
                    String result = get();
                    setResult(AnalysisResultFormatter.forDisplay(result));
                    statusLabel.setText("Completed (" + elapsedSeconds + "s)");
                } catch (CancellationException exc) {
                    setResult("Request was cancelled.");
                    statusLabel.setText("Cancelled");
                } catch (InterruptedException exc) {
                    setResult("Request was interrupted.");
                    statusLabel.setText("Interrupted");
                    Thread.currentThread().interrupt();
                } catch (Exception exc) {
                    String errorMessage = BackendErrorMessage.forException(exc);
                    setResult(errorMessage);
                    statusLabel.setText("Failed (" + elapsedSeconds + "s)");
                    api.logging().logToError("AI Analyzer backend request failed", exc);
                }
            }
        };
        activeWorker = worker;
        worker.execute();
    }

    private void cancelActiveWorker() {
        if (activeWorker != null && !activeWorker.isDone()) {
            activeWorker.cancel(true);
            activeWorker = null;
        }
        stopElapsedTimer();
        cancelButton.setEnabled(false);
    }

    private void startElapsedTimer() {
        stopElapsedTimer();
        elapsedTimer = new Timer(1000, ignored -> {
            elapsedSeconds++;
            statusLabel.setText(statusLabel.getText().replaceAll("\\(\\d+s\\)", "").trim() + " (" + elapsedSeconds + "s)");
        });
        elapsedTimer.start();
    }

    private void stopElapsedTimer() {
        if (elapsedTimer != null) {
            elapsedTimer.stop();
            elapsedTimer = null;
        }
    }

    private void setResult(String text) {
        SwingUtilities.invokeLater(() -> resultArea.setText(text));
    }

    private interface BackendTask {
        String run() throws Exception;
    }
}
