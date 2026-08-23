/**
 * SmartSalary India — Centralized Frontend Client Utilities
 * Handles:
 *  1. INR Number Formatting (Lakh/Crore System)
 *  2. Interactive Period Multipliers (Monthly, 3M, 6M, Annual)
 *  3. Calculation Result Copy Summary & Clipboard
 *  4. AI Drawer context binding
 *  5. Toast and Feedback Alerts
 */

function formatINR(val) {
  const num = parseFloat(val);
  if (isNaN(num)) return '₹0';
  return '₹' + num.toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 0 });
}

function setPeriodMultiplier(multiplier, periodLabel, btnElement) {
  // Update active tab buttons
  const buttons = document.querySelectorAll('.period-btn');
  buttons.forEach(btn => {
    btn.classList.remove('bg-indigo-50', 'dark:bg-indigo-950', 'text-indigo-700', 'dark:text-indigo-300', 'font-bold', 'shadow-xs');
    btn.classList.add('text-slate-600', 'dark:text-slate-400');
  });
  if (btnElement) {
    btnElement.classList.remove('text-slate-600', 'dark:text-slate-400');
    btnElement.classList.add('bg-indigo-50', 'dark:bg-indigo-950', 'text-indigo-700', 'dark:text-indigo-300', 'font-bold', 'shadow-xs');
  }

  // Update all elements with data-annual-val
  const periodicElements = document.querySelectorAll('[data-annual-val]');
  periodicElements.forEach(el => {
    const annualVal = parseFloat(el.getAttribute('data-annual-val'));
    if (!isNaN(annualVal)) {
      const derived = (annualVal / 12) * multiplier;
      const prefix = el.getAttribute('data-val-prefix') || '';
      el.innerText = prefix + formatINR(derived);
    }
  });

  const periodDisplay = document.getElementById('active-period-label');
  if (periodDisplay) {
    periodDisplay.innerText = periodLabel;
  }
}

async function copyCalculationSummary(annualGross, takeHome, tax, pf, pt) {
  const summaryText = `SmartSalary India — Calculation Summary
=============================================
Annual Gross CTC: ${formatINR(annualGross)}
Estimated Net Take-Home: ${formatINR(takeHome)} / yr (${formatINR(takeHome / 12)} / mo)
Total Income Tax: ${formatINR(tax)}
Employee EPF (12%): ${formatINR(pf)}
Professional Tax: ${formatINR(pt)}
=============================================
Verified Statutory Engine • SmartSalary.IN`;

  try {
    await navigator.clipboard.writeText(summaryText);
    showToast('Summary copied to clipboard!', 'success');
  } catch (err) {
    showToast('Failed to copy summary to clipboard', 'error');
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container') || createToastContainer();
  const toast = document.createElement('div');
  const bgColor = type === 'success' ? 'bg-emerald-600 text-white' : type === 'error' ? 'bg-rose-600 text-white' : 'bg-slate-900 text-white';
  toast.className = `${bgColor} px-4 py-2.5 rounded-xl shadow-lg text-xs font-semibold flex items-center gap-2 transition-all transform duration-300 translate-y-2 opacity-0`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none';
  document.body.appendChild(container);
  return container;
}

window.formatINR = formatINR;
window.setPeriodMultiplier = setPeriodMultiplier;
window.copyCalculationSummary = copyCalculationSummary;
window.showToast = showToast;
