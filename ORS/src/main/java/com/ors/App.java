package com.ors;

import java.awt.BorderLayout;
import java.awt.CardLayout;
import java.awt.Color;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;
import java.awt.event.ActionEvent;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.Locale;
import java.util.Random;

import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JPasswordField;
import javax.swing.JScrollPane;
import javax.swing.JTabbedPane;
import javax.swing.JTextArea;
import javax.swing.JTextField;
import javax.swing.SwingConstants;
import javax.swing.SwingUtilities;
import javax.swing.border.EmptyBorder;

public class App {
    public static void main(String[] args) {
        try {
            Database.initialize();
        } catch (SQLException e) {
            JOptionPane.showMessageDialog(null, "Database could not be initialized: " + e.getMessage(), "Error", JOptionPane.ERROR_MESSAGE);
            return;
        }

        SwingUtilities.invokeLater(() -> {
            ORSFrame frame = new ORSFrame();
            frame.setVisible(true);
        });
    }
}

class Database {
    private static final String DB_URL = "jdbc:sqlite:reservations.db";

    static void initialize() throws SQLException {
        try (Connection conn = DriverManager.getConnection(DB_URL)) {
            try (Statement stmt = conn.createStatement()) {
                stmt.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL)");
                stmt.execute("CREATE TABLE IF NOT EXISTS reservations (pnr TEXT PRIMARY KEY, passenger_name TEXT NOT NULL, " +
                        "train_number INTEGER NOT NULL, train_name TEXT NOT NULL, class_type TEXT NOT NULL, " +
                        "journey_date TEXT NOT NULL, source_station TEXT NOT NULL, destination_station TEXT NOT NULL)");
                // Seed a default user for testing.
                try (PreparedStatement ps = conn.prepareStatement("INSERT OR IGNORE INTO users(username,password) VALUES (?, ?)")) {
                    ps.setString(1, "admin");
                    ps.setString(2, "admin");
                    ps.executeUpdate();
                }
            }
        } catch (SQLException e) {
            throw e;
        }
    }

    static boolean validateLogin(String username, String password) {
        String sql = "SELECT 1 FROM users WHERE username = ? AND password = ?";
        try (Connection conn = DriverManager.getConnection(DB_URL);
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, username);
            ps.setString(2, password);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next();
            }
        } catch (SQLException e) {
            return false;
        }
    }

    static String addReservation(String passengerName, String trainNumber, String trainName,
                                  String classType, String journeyDate, String sourceStation,
                                  String destinationStation) {
        String pnr = generatePnr();
        String sql = "INSERT INTO reservations(pnr, passenger_name, train_number, train_name, class_type, journey_date, source_station, destination_station) VALUES (?, ?, ?, ?, ?, ?, ?, ?)";
        try (Connection conn = DriverManager.getConnection(DB_URL);
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, pnr);
            ps.setString(2, passengerName);
            ps.setInt(3, Integer.parseInt(trainNumber));
            ps.setString(4, trainName);
            ps.setString(5, classType);
            ps.setString(6, journeyDate);
            ps.setString(7, sourceStation);
            ps.setString(8, destinationStation);
            ps.executeUpdate();
            return pnr;
        } catch (SQLException e) {
            throw new RuntimeException("Unable to save reservation: " + e.getMessage(), e);
        }
    }

    static Reservation getReservation(String pnr) {
        String sql = "SELECT * FROM reservations WHERE pnr = ?";
        try (Connection conn = DriverManager.getConnection(DB_URL);
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, pnr);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return new Reservation(
                            rs.getString("pnr"),
                            rs.getString("passenger_name"),
                            rs.getInt("train_number"),
                            rs.getString("train_name"),
                            rs.getString("class_type"),
                            rs.getString("journey_date"),
                            rs.getString("source_station"),
                            rs.getString("destination_station")
                    );
                }
            }
        } catch (SQLException e) {
            throw new RuntimeException("Unable to fetch reservation: " + e.getMessage(), e);
        }
        return null;
    }

    static boolean deleteReservation(String pnr) {
        String sql = "DELETE FROM reservations WHERE pnr = ?";
        try (Connection conn = DriverManager.getConnection(DB_URL);
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, pnr);
            return ps.executeUpdate() == 1;
        } catch (SQLException e) {
            return false;
        }
    }

    private static String generatePnr() {
        String chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
        Random r = new Random();
        StringBuilder sb = new StringBuilder();
        do {
            sb.setLength(0);
            for (int i = 0; i < 8; i++) {
                sb.append(chars.charAt(r.nextInt(chars.length())));
            }
        } while (getReservation(sb.toString()) != null);
        return sb.toString();
    }
}

class Reservation {
    String pnr;
    String passengerName;
    int trainNumber;
    String trainName;
    String classType;
    String journeyDate;
    String sourceStation;
    String destinationStation;

    Reservation(String pnr, String passengerName, int trainNumber, String trainName, String classType,
                String journeyDate, String sourceStation, String destinationStation) {
        this.pnr = pnr;
        this.passengerName = passengerName;
        this.trainNumber = trainNumber;
        this.trainName = trainName;
        this.classType = classType;
        this.journeyDate = journeyDate;
        this.sourceStation = sourceStation;
        this.destinationStation = destinationStation;
    }
}

class ORSFrame extends JFrame {
    private final CardLayout cardLayout = new CardLayout();
    private final JPanel cardPanel = new JPanel(cardLayout);

    ORSFrame() {
        super("Online Reservation System");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setSize(900, 620);
        setLocationRelativeTo(null);

        JPanel loginPanel = createLoginPanel();
        JPanel appPanel = createDashboardPanel();

        cardPanel.add(loginPanel, "LOGIN");
        cardPanel.add(appPanel, "APPLICATION");
        add(cardPanel);

        cardLayout.show(cardPanel, "LOGIN");
    }

    private JPanel createLoginPanel() {
        JPanel panel = new JPanel(new BorderLayout());
        panel.setBackground(new Color(246, 248, 250));

        JLabel title = new JLabel("Online Reservation System", SwingConstants.CENTER);
        title.setFont(new Font("SansSerif", Font.BOLD, 26));
        title.setBorder(new EmptyBorder(30, 0, 20, 0));

        JPanel formPanel = new JPanel(new GridBagLayout());
        formPanel.setOpaque(false);
        GridBagConstraints c = new GridBagConstraints();
        c.insets = new Insets(8, 8, 8, 8);

        JLabel userLabel = new JLabel("Username:");
        JLabel passLabel = new JLabel("Password:");
        JTextField usernameField = new JTextField(20);
        JPasswordField passwordField = new JPasswordField(20);
        JButton loginButton = new JButton("Login");
        JLabel message = new JLabel("", SwingConstants.CENTER);
        message.setForeground(Color.RED);

        c.gridx = 0;
        c.gridy = 0;
        formPanel.add(userLabel, c);
        c.gridx = 1;
        formPanel.add(usernameField, c);

        c.gridx = 0;
        c.gridy = 1;
        formPanel.add(passLabel, c);
        c.gridx = 1;
        formPanel.add(passwordField, c);

        c.gridx = 0;
        c.gridy = 2;
        c.gridwidth = 2;
        formPanel.add(loginButton, c);

        c.gridy = 3;
        formPanel.add(message, c);

        loginButton.addActionListener((ActionEvent e) -> {
            String username = usernameField.getText().trim();
            String password = new String(passwordField.getPassword());
            if (Database.validateLogin(username, password)) {
                message.setText("");
                cardLayout.show(cardPanel, "APPLICATION");
            } else {
                message.setText("Invalid username or password.");
            }
        });

        panel.add(title, BorderLayout.NORTH);
        panel.add(formPanel, BorderLayout.CENTER);
        return panel;
    }

    private JPanel createDashboardPanel() {
        JPanel panel = new JPanel(new BorderLayout(12, 12));
        panel.setBorder(new EmptyBorder(20, 20, 20, 20));
        panel.setBackground(new Color(251, 253, 255));

        JLabel heading = new JLabel("Train Reservation Dashboard");
        heading.setFont(new Font("SansSerif", Font.BOLD, 24));
        heading.setBorder(new EmptyBorder(0, 0, 16, 0));

        JTabbedPane tabs = new JTabbedPane();
        JPanel bookingPanel = createBookingPanel();
        JPanel cancelPanel = createCancellationPanel();
        tabs.addTab("Book Ticket", bookingPanel);
        tabs.addTab("Cancel Booking", cancelPanel);

        panel.add(heading, BorderLayout.NORTH);
        panel.add(tabs, BorderLayout.CENTER);
        return panel;
    }

    private JPanel createBookingPanel() {
        JPanel panel = new JPanel(new GridBagLayout());
        panel.setBorder(new EmptyBorder(15, 15, 15, 15));
        GridBagConstraints c = new GridBagConstraints();
        c.insets = new Insets(8, 8, 8, 8);
        c.fill = GridBagConstraints.HORIZONTAL;

        JLabel passengerLabel = new JLabel("Passenger Name:");
        JTextField passengerName = new JTextField(25);
        JLabel trainNoLabel = new JLabel("Train Number:");
        JTextField trainNumber = new JTextField(12);
        JLabel trainNameLabel = new JLabel("Train Name:");
        JTextField trainName = new JTextField(25);
        JLabel classLabel = new JLabel("Class Type:");
        JComboBox<String> classType = new JComboBox<>(new String[]{"Sleeper", "AC 2 Tier", "AC 3 Tier", "Chair Car", "Executive"});
        JLabel dateLabel = new JLabel("Date of Journey:");
        JTextField dateOfJourney = new JTextField(12);
        JLabel sourceLabel = new JLabel("Source Station:");
        JTextField sourceStation = new JTextField(20);
        JLabel destLabel = new JLabel("Destination Station:");
        JTextField destinationStation = new JTextField(20);

        JTextArea bookingOutput = new JTextArea(8, 40);
        bookingOutput.setEditable(false);
        bookingOutput.setLineWrap(true);
        bookingOutput.setWrapStyleWord(true);
        JScrollPane scroll = new JScrollPane(bookingOutput);

        JButton bookButton = new JButton("Book Ticket");

        c.gridx = 0;
        c.gridy = 0;
        panel.add(passengerLabel, c);
        c.gridx = 1;
        panel.add(passengerName, c);

        c.gridx = 0;
        c.gridy = 1;
        panel.add(trainNoLabel, c);
        c.gridx = 1;
        panel.add(trainNumber, c);

        c.gridx = 0;
        c.gridy = 2;
        panel.add(trainNameLabel, c);
        c.gridx = 1;
        panel.add(trainName, c);

        c.gridx = 0;
        c.gridy = 3;
        panel.add(classLabel, c);
        c.gridx = 1;
        panel.add(classType, c);

        c.gridx = 0;
        c.gridy = 4;
        panel.add(dateLabel, c);
        c.gridx = 1;
        panel.add(dateOfJourney, c);

        c.gridx = 0;
        c.gridy = 5;
        panel.add(sourceLabel, c);
        c.gridx = 1;
        panel.add(sourceStation, c);

        c.gridx = 0;
        c.gridy = 6;
        panel.add(destLabel, c);
        c.gridx = 1;
        panel.add(destinationStation, c);

        c.gridx = 0;
        c.gridy = 7;
        c.gridwidth = 2;
        panel.add(bookButton, c);

        c.gridy = 8;
        c.gridwidth = 2;
        c.weightx = 1.0;
        c.weighty = 1.0;
        c.fill = GridBagConstraints.BOTH;
        panel.add(scroll, c);

        bookButton.addActionListener((ActionEvent e) -> {
            String output = validateAndBook(passengerName.getText(), trainNumber.getText(), trainName.getText(),
                    classType.getSelectedItem().toString(), dateOfJourney.getText(), sourceStation.getText(),
                    destinationStation.getText());
            if (output.startsWith("ERROR:")) {
                bookingOutput.setText(output.replace("ERROR:", ""));
            } else {
                bookingOutput.setText(output);
            }
        });

        return panel;
    }

    private JPanel createCancellationPanel() {
        JPanel panel = new JPanel(new GridBagLayout());
        panel.setBorder(new EmptyBorder(15, 15, 15, 15));
        GridBagConstraints c = new GridBagConstraints();
        c.insets = new Insets(8, 8, 8, 8);

        JLabel pnrLabel = new JLabel("PNR Number:");
        JTextField pnrField = new JTextField(20);
        JButton findButton = new JButton("Find Booking");
        JButton cancelButton = new JButton("Cancel Booking");
        JButton clearButton = new JButton("Clear");
        JTextArea cancellationOutput = new JTextArea(10, 40);
        cancellationOutput.setEditable(false);
        cancellationOutput.setLineWrap(true);
        cancellationOutput.setWrapStyleWord(true);
        JScrollPane scroll = new JScrollPane(cancellationOutput);

        c.gridx = 0;
        c.gridy = 0;
        panel.add(pnrLabel, c);
        c.gridx = 1;
        panel.add(pnrField, c);

        c.gridx = 0;
        c.gridy = 1;
        c.gridwidth = 2;
        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        buttonPanel.add(findButton);
        buttonPanel.add(cancelButton);
        buttonPanel.add(clearButton);
        panel.add(buttonPanel, c);

        c.gridy = 2;
        c.gridwidth = 2;
        c.fill = GridBagConstraints.BOTH;
        c.weightx = 1;
        c.weighty = 1;
        panel.add(scroll, c);

        findButton.addActionListener((ActionEvent e) -> {
            String pnr = pnrField.getText().trim().toUpperCase(Locale.ROOT);
            Reservation r = Database.getReservation(pnr);
            if (r == null) {
                cancellationOutput.setText("No booking found for PNR: " + pnr);
            } else {
                cancellationOutput.setText("Booking found:\n" + formatReservation(r));
            }
        });

        cancelButton.addActionListener((ActionEvent e) -> {
            String pnr = pnrField.getText().trim().toUpperCase(Locale.ROOT);
            Reservation r = Database.getReservation(pnr);
            if (r == null) {
                cancellationOutput.setText("No booking found for PNR: " + pnr);
                return;
            }
            int answer = JOptionPane.showConfirmDialog(this,
                    "Are you sure?\n" + formatReservation(r),
                    "Confirm Cancellation",
                    JOptionPane.YES_NO_OPTION);
            if (answer == JOptionPane.YES_OPTION) {
                boolean deleted = Database.deleteReservation(pnr);
                if (deleted) {
                    cancellationOutput.setText("Booking with PNR " + pnr + " has been cancelled.");
                } else {
                    cancellationOutput.setText("Unable to cancel booking with PNR " + pnr);
                }
            } else {
                cancellationOutput.setText("Cancellation cancelled for PNR " + pnr);
            }
        });

        clearButton.addActionListener((ActionEvent e) -> {
            pnrField.setText("");
            cancellationOutput.setText("");
        });

        return panel;
    }

    private String validateAndBook(String passengerName, String trainNumber, String trainName,
                                    String classType, String journeyDate, String sourceStation,
                                    String destinationStation) {
        if (passengerName == null || passengerName.trim().isEmpty()) {
            return "ERROR: Passenger name is required";
        }
        if (trainNumber == null || trainNumber.trim().isEmpty() || !trainNumber.matches("\\d+")) {
            return "ERROR: Train number must be numeric";
        }
        if (trainName == null || trainName.trim().isEmpty()) {
            return "ERROR: Train name is required";
        }
        if (classType == null || classType.trim().isEmpty()) {
            return "ERROR: Class type is required";
        }
        if (journeyDate == null || journeyDate.trim().isEmpty()) {
            return "ERROR: Date of journey is required";
        }
        if (sourceStation == null || sourceStation.trim().isEmpty()) {
            return "ERROR: Source station is required";
        }
        if (destinationStation == null || destinationStation.trim().isEmpty()) {
            return "ERROR: Destination station is required";
        }

        try {
            LocalDate.parse(journeyDate.trim());
        } catch (DateTimeParseException ex) {
            return "ERROR: Enter date in valid format (yyyy-MM-dd)";
        }

        if (sourceStation.equalsIgnoreCase(destinationStation)) {
            return "ERROR: Source and destination cannot be the same";
        }

        String pnr = Database.addReservation(passengerName.trim(), trainNumber.trim(), trainName.trim(), classType,
                journeyDate.trim(), sourceStation.trim(), destinationStation.trim());

        return "Booking confirmed.\nPNR: " + pnr + "\n" + formatReservation(new Reservation(
                pnr, passengerName.trim(), Integer.parseInt(trainNumber.trim()), trainName.trim(), classType,
                journeyDate.trim(), sourceStation.trim(), destinationStation.trim()));
    }

    private String formatReservation(Reservation r) {
        return "Passenger: " + r.passengerName + "\n" +
                "Train: " + r.trainNumber + " - " + r.trainName + "\n" +
                "Class: " + r.classType + "\n" +
                "Date: " + r.journeyDate + "\n" +
                "From: " + r.sourceStation + "\n" +
                "To: " + r.destinationStation + "\n" +
                "PNR: " + r.pnr;
    }
}
