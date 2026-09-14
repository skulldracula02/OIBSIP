package com.example.unitconverter;

import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class MainActivity extends AppCompatActivity {

    private EditText valueInput;
    private Spinner categorySpinner, fromSpinner, toSpinner;
    private TextView resultText;
    private Button convertButton;

    private final Map<String, List<String>> categoryUnits = new LinkedHashMap<>();
    private final Map<String, Map<String, Double>> conversionFactors = new LinkedHashMap<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        valueInput = findViewById(R.id.valueInput);
        categorySpinner = findViewById(R.id.categorySpinner);
        fromSpinner = findViewById(R.id.fromSpinner);
        toSpinner = findViewById(R.id.toSpinner);
        resultText = findViewById(R.id.resultText);
        convertButton = findViewById(R.id.convertButton);

        categoryUnits.put("Length", List.of("Meters", "Centimeters", "Inches", "Feet"));
        categoryUnits.put("Weight", List.of("Kilograms", "Grams", "Pounds", "Ounces"));
        categoryUnits.put("Temperature", List.of("Celsius", "Fahrenheit", "Kelvin"));

        conversionFactors.put("Length", new LinkedHashMap<>() {{
            put("Meters", 1.0);
            put("Centimeters", 0.01);
            put("Inches", 0.0254);
            put("Feet", 0.3048);
        }});

        conversionFactors.put("Weight", new LinkedHashMap<>() {{
            put("Kilograms", 1.0);
            put("Grams", 0.001);
            put("Pounds", 0.45359237);
            put("Ounces", 0.0283495231);
        }});

        conversionFactors.put("Temperature", new LinkedHashMap<>() {{
            put("Celsius", 1.0);
            put("Fahrenheit", 1.0);
            put("Kelvin", 1.0);
        }});

        ArrayAdapter<String> categoryAdapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, new ArrayList<>(categoryUnits.keySet()));
        categoryAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        categorySpinner.setAdapter(categoryAdapter);

        updateUnitSpinners("Length");

        categorySpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                String category = parent.getItemAtPosition(position).toString();
                updateUnitSpinners(category);
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });

        convertButton.setOnClickListener(v -> convertValue());
    }

    private void updateUnitSpinners(String category) {
        List<String> units = categoryUnits.get(category);
        if (units == null) return;

        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, units);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        fromSpinner.setAdapter(adapter);
        toSpinner.setAdapter(adapter);

        fromSpinner.setSelection(0);
        toSpinner.setSelection(Math.min(1, units.size() - 1));
    }

    private void convertValue() {
        String inputText = valueInput.getText().toString().trim();
        if (inputText.isEmpty()) {
            Toast.makeText(this, "Please enter a value", Toast.LENGTH_SHORT).show();
            return;
        }

        double inputValue;
        try {
            inputValue = Double.parseDouble(inputText);
        } catch (NumberFormatException e) {
            Toast.makeText(this, "Please enter a valid number", Toast.LENGTH_SHORT).show();
            return;
        }

        String category = categorySpinner.getSelectedItem().toString();
        String fromUnit = fromSpinner.getSelectedItem().toString();
        String toUnit = toSpinner.getSelectedItem().toString();

        if ("Temperature".equals(category)) {
            double result = convertTemperature(inputValue, fromUnit, toUnit);
            resultText.setText(String.format("%.2f %s = %.2f %s", inputValue, fromUnit, result, toUnit));
        } else {
            double baseValue = inputValue * getFactor(category, fromUnit);
            double result = baseValue / getFactor(category, toUnit);
            resultText.setText(String.format("%.2f %s = %.2f %s", inputValue, fromUnit, result, toUnit));
        }
    }

    private double getFactor(String category, String unit) {
        return conversionFactors.get(category).get(unit);
    }

    private double convertTemperature(double value, String fromUnit, String toUnit) {
        double celsius;
        switch (fromUnit) {
            case "Celsius":
                celsius = value;
                break;
            case "Fahrenheit":
                celsius = (value - 32) * 5 / 9;
                break;
            case "Kelvin":
                celsius = value - 273.15;
                break;
            default:
                celsius = value;
        }

        switch (toUnit) {
            case "Celsius":
                return celsius;
            case "Fahrenheit":
                return (celsius * 9 / 5) + 32;
            case "Kelvin":
                return celsius + 273.15;
            default:
                return celsius;
        }
    }
}
