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
import com.burpai.core.StreamCallback;

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
import java.util.concurrent.atomic.AtomicReference;

public class Extension implements BurpExtension, ContextMenuItemsProvider {
    private MontoyaApi api;
    private ExtensionSettings settings;
    private JTextField backendUrlField;
    private JTextField tokenField;
    private JTextArea resultArea;
    private JButton cancelButton;
    private JLabel statusLabel;
    private SwingWorker<?, ?> activeWorker;
    private Timer elapsedTimer;
    private int elapsedSeconds;
    private String currentMode;

    @Override
    public void initialize(MontoyaApi api) {
        this.api = api;
        this.settings = new ExtensionSettings(api);
        api.extension().setName("AI HTTP 分析器");
        api.userInterface().registerSuiteTab("AI Analyzer", createPanel());
        api.userInterface().registerContextMenuItemsProvider(this);
        api.logging().logToOutput("AI HTTP 分析器已加载。");
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

        backendUrlField = new JTextField(settings.getBackendUrl());
        tokenField = new JTextField(settings.getBackendToken());

        JButton healthButton = new JButton("测试后端");
        healthButton.addActionListener(ignored -> testBackend());
        JButton saveButton = new JButton("保存设置");
        saveButton.addActionListener(ignored -> saveSettings());

        JPanel settingsPanel = new JPanel();
        settingsPanel.setLayout(new BoxLayout(settingsPanel, BoxLayout.Y_AXIS));
        settingsPanel.setBorder(BorderFactory.createEmptyBorder(8, 8, 8, 8));
        settingsPanel.add(labeledRow("后端 URL", backendUrlField));
        settingsPanel.add(Box.createVerticalStrut(4));
        settingsPanel.add(labeledRow("后端 Token", tokenField));
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

        statusLabel = new JLabel("就绪");
        statusLabel.setBorder(BorderFactory.createEmptyBorder(2, 4, 2, 4));

        cancelButton = new JButton("取消");
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
        setResult("设置已保存，将在 Burp 重启后保持生效。");
        api.logging().logToOutput("扩展设置已保存。");
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
            setResult("当前上下文中没有可用的请求。");
            return;
        }
        String request = message.request.toString();
        String response = message.response == null ? null : message.response.toString();
        String targetUrl = message.targetUrl;
        PreparedHttpMessage prepared = HttpMessageFilter.prepare(request, response, targetUrl);
        String json = AnalysisRequestBuilder.build("burp", mode, prepared);
        currentMode = mode;
        String loadingMessage = response == null
                ? "正在分析选中的请求..."
                : "正在分析选中的请求和响应...";
        runStreamInBackground(loadingMessage, json, mode);
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
        runInBackground("正在测试后端连接...", () -> {
            BackendClient client = new BackendClient(backendUrlField.getText(), tokenField.getText());
            return client.health() ? "后端健康检查成功。" : "后端健康检查失败。";
        });
    }

    private void runInBackground(String loadingMessage, BackendTask task) {
        cancelActiveWorker();
        setResult(loadingMessage);
        statusLabel.setText(loadingMessage);
        cancelButton.setEnabled(true);
        elapsedSeconds = 0;
        startElapsedTimer();

        SwingWorker<Void, StreamChunk> worker = new SwingWorker<Void, StreamChunk>() {
            @Override
            protected Void doInBackground() throws Exception {
                String result = task.run();
                publish(new StreamChunk("result", result));
                return null;
            }

            @Override
            protected void process(List<StreamChunk> chunks) {
                for (StreamChunk chunk : chunks) {
                    if ("result".equals(chunk.type)) {
                        setResult(chunk.data);
                    }
                }
            }

            @Override
            protected void done() {
                stopElapsedTimer();
                cancelButton.setEnabled(false);
                try {
                    get();
                    statusLabel.setText("完成 (" + elapsedSeconds + "s)");
                } catch (CancellationException exc) {
                    setResult("请求已取消。");
                    statusLabel.setText("已取消");
                } catch (InterruptedException exc) {
                    setResult("请求被中断。");
                    statusLabel.setText("已中断");
                    Thread.currentThread().interrupt();
                } catch (Exception exc) {
                    String errorMessage = BackendErrorMessage.forException(exc);
                    setResult(errorMessage);
                    statusLabel.setText("失败 (" + elapsedSeconds + "s)");
                    api.logging().logToError("AI 分析器后端请求失败", exc);
                }
            }
        };
        activeWorker = worker;
        worker.execute();
    }

    private interface BackendTask {
        String run() throws Exception;
    }

    private void runStreamInBackground(String loadingMessage, String json, String mode) {
        cancelActiveWorker();
        setResult(loadingMessage);
        statusLabel.setText(loadingMessage);
        cancelButton.setEnabled(true);
        elapsedSeconds = 0;
        startElapsedTimer();

        AtomicReference<String> lastRawResult = new AtomicReference<>();
        SwingWorker<Void, StreamChunk> worker = new SwingWorker<Void, StreamChunk>() {
            @Override
            protected Void doInBackground() throws Exception {
                BackendClient client = new BackendClient(backendUrlField.getText(), tokenField.getText());
                client.analyzeStream(json, new StreamCallback() {
                    @Override
                    public void onStatus(String status) {
                        publish(new StreamChunk("status", status));
                    }

                    @Override
                    public void onContent(String text) {
                        publish(new StreamChunk("content", text));
                    }

                    @Override
                    public void onResult(String rawJson) {
                        lastRawResult.set(rawJson);
                        publish(new StreamChunk("result", rawJson));
                    }

                    @Override
                    public void onError(Exception e) {
                        publish(new StreamChunk("error", e.getMessage() != null ? e.getMessage() : e.getClass().getName()));
                    }
                });
                return null;
            }

            @Override
            protected void process(List<StreamChunk> chunks) {
                for (StreamChunk chunk : chunks) {
                    switch (chunk.type) {
                        case "status":
                            String statusText = translateStatus(chunk.data);
                            statusLabel.setText(statusText + " (" + elapsedSeconds + "s)");
                            break;
                        case "content":
                            resultArea.append(chunk.data);
                            resultArea.setCaretPosition(resultArea.getDocument().getLength());
                            break;
                        case "result":
                            String formatted = "learn".equals(mode)
                                    ? AnalysisResultFormatter.forLearnDisplay(chunk.data)
                                    : AnalysisResultFormatter.forDisplay(chunk.data);
                            setResult(formatted);
                            break;
                        case "error":
                            setResult(chunk.data);
                            break;
                    }
                }
            }

            @Override
            protected void done() {
                stopElapsedTimer();
                cancelButton.setEnabled(false);
                try {
                    get();
                    if (lastRawResult.get() != null) {
                        statusLabel.setText("完成 (" + elapsedSeconds + "s)");
                    } else {
                        statusLabel.setText("无结果 (" + elapsedSeconds + "s)");
                    }
                } catch (CancellationException exc) {
                    setResult("请求已取消。");
                    statusLabel.setText("已取消");
                } catch (InterruptedException exc) {
                    setResult("请求被中断。");
                    statusLabel.setText("已中断");
                    Thread.currentThread().interrupt();
                } catch (Exception exc) {
                    String errorMessage = BackendErrorMessage.forException(exc);
                    setResult(errorMessage);
                    statusLabel.setText("失败 (" + elapsedSeconds + "s)");
                    api.logging().logToError("AI 分析器后端请求失败", exc);
                }
            }
        };
        activeWorker = worker;
        worker.execute();
    }

    private static String translateStatus(String status) {
        switch (status) {
            case "redacting": return "正在脱敏处理";
            case "calling_provider": return "正在调用大模型";
            case "parsing": return "正在解析结果";
            case "persisted": return "已保存";
            case "failed": return "失败";
            default: return status;
        }
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
        SwingUtilities.invokeLater(() -> {
            resultArea.setText(text);
            resultArea.setCaretPosition(0);
        });
    }

    private static final class StreamChunk {
        final String type;
        final String data;

        StreamChunk(String type, String data) {
            this.type = type;
            this.data = data;
        }
    }
}
