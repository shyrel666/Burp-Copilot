package com.burpai.core;

import burp.api.montoya.MontoyaApi;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.DefaultListModel;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JLabel;
import javax.swing.JList;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextField;
import javax.swing.SwingUtilities;
import javax.swing.SwingWorker;
import java.awt.BorderLayout;
import java.awt.Dimension;
import java.util.List;

/**
 * Swing configuration panel for passive auto-analysis: enable toggle, scope rule
 * management, session submission counter, and a one-click Site Map scan. Embedded
 * into the main extension tab.
 */
public final class AutoAnalysisPanel {
    private final MontoyaApi api;
    private final AutoAnalysisEngine engine;
    private final ScopeRuleStore store;

    private final JPanel panel = new JPanel();
    private final DefaultListModel<String> ruleModel = new DefaultListModel<>();
    private final JLabel counterLabel = new JLabel();
    private final JLabel statusLabel = new JLabel(" ");

    public AutoAnalysisPanel(MontoyaApi api, AutoAnalysisEngine engine) {
        this.api = api;
        this.engine = engine;
        this.store = engine.store();
        build();
        engine.setOnCountChanged(() -> SwingUtilities.invokeLater(this::refreshCounter));
    }

    public JPanel getComponent() {
        return panel;
    }

    private void build() {
        panel.setLayout(new BoxLayout(panel, BoxLayout.Y_AXIS));
        panel.setBorder(BorderFactory.createTitledBorder("自动分析（被动 · 仅授权测试）"));

        JCheckBox enabledBox = new JCheckBox("启用自动分析（对 Scope 内代理流量自动提交）", store.isEnabled());
        enabledBox.addActionListener(ignored -> store.setEnabled(enabledBox.isSelected()));
        enabledBox.setAlignmentX(java.awt.Component.LEFT_ALIGNMENT);
        panel.add(enabledBox);
        panel.add(Box.createVerticalStrut(4));

        reloadRules();
        JList<String> ruleList = new JList<>(ruleModel);
        JScrollPane ruleScroll = new JScrollPane(ruleList);
        ruleScroll.setPreferredSize(new Dimension(360, 70));
        ruleScroll.setMaximumSize(new Dimension(Integer.MAX_VALUE, 80));
        panel.add(ruleScroll);

        JTextField ruleField = new JTextField();
        JButton addButton = new JButton("添加规则");
        JButton removeButton = new JButton("删除所选");
        addButton.addActionListener(ignored -> addRule(ruleField));
        removeButton.addActionListener(ignored -> removeSelected(ruleList));

        JPanel ruleControls = new JPanel(new BorderLayout(6, 0));
        ruleControls.add(new JLabel("规则(glob，如 *.target.com)："), BorderLayout.WEST);
        ruleControls.add(ruleField, BorderLayout.CENTER);
        JPanel ruleButtons = new JPanel();
        ruleButtons.add(addButton);
        ruleButtons.add(removeButton);
        ruleControls.add(ruleButtons, BorderLayout.EAST);
        ruleControls.setMaximumSize(new Dimension(Integer.MAX_VALUE, ruleField.getPreferredSize().height + 8));
        panel.add(ruleControls);
        panel.add(Box.createVerticalStrut(4));

        JTextField siteMapHostField = new JTextField();
        JButton scanButton = new JButton("分析 Site Map");
        scanButton.addActionListener(ignored -> scanSiteMap(siteMapHostField.getText(), scanButton));
        JPanel scanRow = new JPanel(new BorderLayout(6, 0));
        scanRow.add(new JLabel("Site Map 主机过滤(可空)："), BorderLayout.WEST);
        scanRow.add(siteMapHostField, BorderLayout.CENTER);
        scanRow.add(scanButton, BorderLayout.EAST);
        scanRow.setMaximumSize(new Dimension(Integer.MAX_VALUE, siteMapHostField.getPreferredSize().height + 8));
        panel.add(scanRow);
        panel.add(Box.createVerticalStrut(4));

        refreshCounter();
        counterLabel.setAlignmentX(java.awt.Component.LEFT_ALIGNMENT);
        statusLabel.setAlignmentX(java.awt.Component.LEFT_ALIGNMENT);
        panel.add(counterLabel);
        panel.add(statusLabel);
    }

    private void addRule(JTextField ruleField) {
        try {
            store.addRule(ruleField.getText());
            ruleField.setText("");
            reloadRules();
            setStatus(" ");
        } catch (ScopeRuleStore.ValidationException ex) {
            setStatus(ex.getMessage());
        }
    }

    private void removeSelected(JList<String> ruleList) {
        String selected = ruleList.getSelectedValue();
        if (selected != null) {
            store.removeRule(selected);
            reloadRules();
        }
    }

    private void reloadRules() {
        ruleModel.clear();
        List<String> rules = store.getRules();
        for (String rule : rules) {
            ruleModel.addElement(rule);
        }
    }

    private void scanSiteMap(String hostFilter, JButton scanButton) {
        scanButton.setEnabled(false);
        setStatus("正在分析 Site Map...");
        new SwingWorker<Integer, Void>() {
            @Override
            protected Integer doInBackground() {
                return engine.scanSiteMap(hostFilter);
            }

            @Override
            protected void done() {
                scanButton.setEnabled(true);
                try {
                    setStatus("已提交 " + get() + " 条 Site Map 流量进行分析。");
                } catch (Exception ex) {
                    setStatus("Site Map 分析失败。");
                    api.logging().logToError("Site Map 分析失败", ex);
                }
            }
        }.execute();
    }

    private void refreshCounter() {
        counterLabel.setText("本次会话已提交：" + engine.sessionCount() + " 条");
    }

    private void setStatus(String text) {
        SwingUtilities.invokeLater(() -> statusLabel.setText(text));
    }
}
