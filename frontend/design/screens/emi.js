/* Reducing-balance EMI with the moratorium behaviour concessional schemes use.
   Ported from src/features/calculator/emi.ts so the prototype's figures match
   the app's offline engine exactly. All money in whole rupees. */
(function () {
  function monthlyRate(annualPct) { return annualPct / 12 / 100; }

  function flatEmi(principal, annualPct, months) {
    if (months <= 0 || principal <= 0) return 0;
    var r = monthlyRate(annualPct);
    if (r === 0) return principal / months;
    var g = Math.pow(1 + r, months);
    return (principal * r * g) / (g - 1);
  }

  function calculateEmi(input) {
    var principal = input.principal;
    var r = monthlyRate(input.annualRatePct);
    var tenure = input.tenureMonths;
    var mor = input.moratoriumMonths || 0;
    var capitalise = (input.moratoriumTreatment || 'CAPITALISE') === 'CAPITALISE';
    var schedule = [];
    var balance = principal;
    var moratoriumInterest = 0;
    var m;

    for (m = 1; m <= mor; m++) {
      var mi = balance * r;
      moratoriumInterest += mi;
      if (capitalise) {
        schedule.push({ month: m, opening: balance, emi: 0, interest: mi,
                        principal: 0, closing: balance + mi, holiday: true });
        balance += mi;
      } else {
        schedule.push({ month: m, opening: balance, emi: mi, interest: mi,
                        principal: 0, closing: balance, holiday: true });
      }
    }

    var amortised = balance;
    var emi = flatEmi(amortised, input.annualRatePct, tenure);
    var totalInterest = 0;

    for (m = 1; m <= tenure; m++) {
      var interest = balance * r;
      var pay = (m === tenure) ? balance + interest : emi;
      var principalPart = pay - interest;
      var closing = Math.max(balance - principalPart, 0);
      totalInterest += interest;
      schedule.push({ month: mor + m, opening: balance, emi: pay, interest: interest,
                      principal: principalPart, closing: closing, holiday: false });
      balance = closing;
    }

    /* Derived from the schedule rather than computed separately, so the headline
       total always equals the instalments the user can add up on screen.
       SERVICE_MONTHLY pays the holiday interest during the holiday (those rows
       carry an emi); CAPITALISE rolls it into the principal and recovers it
       through the instalments (those rows carry emi: 0). */
    var totalPayable = schedule.reduce(function (sum, row) { return sum + row.emi; }, 0);

    return {
      emi: emi,
      amortisedPrincipal: amortised,
      moratoriumInterest: moratoriumInterest,
      totalInterest: totalInterest,
      totalPayable: totalPayable,
      totalMonths: mor + tenure,
      schedule: schedule
    };
  }

  /* ₹ formatting on the Indian numbering system (lakh / crore grouping). */
  function inr(n) {
    var v = Math.round(n);
    var sign = v < 0 ? '-' : '';
    v = Math.abs(v).toString();
    if (v.length <= 3) return sign + '₹' + v;
    var last3 = v.slice(-3);
    var rest = v.slice(0, -3);
    return sign + '₹' + rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + last3;
  }

  /* Grouped digits with no symbol — for dense tables where a per-cell ₹
     would blow the 390px column budget. The header carries the unit. */
  function plain(n) {
    var v = Math.round(n).toString();
    if (v.length <= 3) return v;
    var last3 = v.slice(-3), rest = v.slice(0, -3);
    return rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + last3;
  }

  /* Compact Indian form, matching src/utils/format.ts: ₹1.4 L / ₹50 L / ₹4.8 cr.
     Trailing zeros are trimmed so 1,40,000 reads "1.4 L", not "1.40 L". */
  function trim(x) { return String(Number(x.toFixed(2))); }

  function compactInr(n) {
    if (n >= 10000000) return '₹' + trim(n / 10000000) + ' cr';
    if (n >= 100000)   return '₹' + trim(n / 100000) + ' L';
    if (n >= 1000)     return '₹' + Number((n / 1000).toFixed(1)) + 'k';
    return inr(n);
  }

  function duration(months) {
    var y = Math.floor(months / 12), m = months % 12;
    if (y && m) return y + 'y ' + m + 'm';
    if (y) return y + (y === 1 ? ' year' : ' years');
    return m + ' months';
  }

  window.EMI = { calculateEmi: calculateEmi, flatEmi: flatEmi, inr: inr,
                 plain: plain, compactInr: compactInr, duration: duration };
})();
