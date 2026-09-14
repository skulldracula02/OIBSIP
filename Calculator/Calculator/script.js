const display = document.getElementById('display');
let currentValue = '';
let previousValue = '';
let operator = null;
let shouldResetDisplay = false;

// Core calculator logic functions
function appendNumber(num) {
    if (shouldResetDisplay) {
        currentValue = num;
        shouldResetDisplay = false;
    } else {
        currentValue += num;
    }
    updateDisplay();
}

function appendOperator(op) {
    if (currentValue === '' && previousValue === '') return;
    
    if (currentValue !== '') {
        if (previousValue !== '' && operator !== null) {
            calculate();
        } else {
            previousValue = currentValue;
        }
        currentValue = '';
    }
    operator = op;
    shouldResetDisplay = true;
}

function appendDecimal() {
    if (shouldResetDisplay) {
        currentValue = '0.';
        shouldResetDisplay = false;
    } else if (!currentValue.includes('.')) {
        currentValue += '.';
    }
    updateDisplay();
}

function deleteLastChar() {
    currentValue = currentValue.slice(0, -1);
    updateDisplay();
}

function clearDisplay() {
    currentValue = '';
    previousValue = '';
    operator = null;
    shouldResetDisplay = false;
    updateDisplay();
}

function calculate() {
    if (operator === null || currentValue === '' || previousValue === '') return;
    
    let result;
    const prev = parseFloat(previousValue);
    const current = parseFloat(currentValue);
    
    switch (operator) {
        case '+':
            result = prev + current;
            break;
        case '-':
            result = prev - current;
            break;
        case '*':
            result = prev * current;
            break;
        case '/':
            // Division by zero prevention
            if (current === 0) {
                display.value = 'Error: Cannot divide by zero';
                currentValue = '';
                previousValue = '';
                operator = null;
                shouldResetDisplay = true;
                return;
            }
            result = prev / current;
            break;
        default:
            return;
    }
    
    currentValue = result.toString();
    previousValue = '';
    operator = null;
    shouldResetDisplay = true;
    updateDisplay();
}

function updateDisplay() {
    display.value = currentValue || '0';
}

// Event listeners setup
function initializeEventListeners() {
    // Number buttons
    document.querySelectorAll('.btn.number').forEach(button => {
        button.addEventListener('click', function() {
            appendNumber(this.dataset.number);
        });
    });
    
    // Operator buttons
    document.querySelectorAll('.btn.operator').forEach(button => {
        button.addEventListener('click', function() {
            appendOperator(this.dataset.operator);
        });
    });
    
    // Decimal button
    document.querySelector('.btn.decimal').addEventListener('click', appendDecimal);
    
    // Equals button
    document.querySelector('.btn.equals').addEventListener('click', calculate);
    
    // Clear button
    document.querySelector('.btn.clear').addEventListener('click', clearDisplay);
    
    // Delete button
    document.querySelector('.btn.delete').addEventListener('click', deleteLastChar);
}

// Initialize display and event listeners on page load
document.addEventListener('DOMContentLoaded', function() {
    updateDisplay();
    initializeEventListeners();
});
