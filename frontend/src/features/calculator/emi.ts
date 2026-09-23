/**
 * Financial Calculator — pure, dependency-free, fully offline.
 *
 * This is deliberately NOT behind the API: a beneficiary on a 2G connection in
 * a village must still be able to work out what they will owe. Keep this file
 * pure so it stays trivially testable and reusable by the backend if needed.
 *
 * All money is in whole rupees. Rounding is applied only at the boundary.
 */

export type MoratoriumTreatment =
  /** Interest accrues during the moratorium and is added to the principal. */
  | 'CAPITALISE'
  /** Borrower pays the accrued interest monthly during the moratorium. */
  | 'SERVICE_MONTHLY';

export type EmiInput = {
  /** Sanctioned loan amount in rupees. */
  principal: number;
  /** Nominal annual interest rate, e.g. 6.5 for 6.5% p.a. */
  annualRatePct: number;
  /** Total repayment tenure in months, EXCLUDING the moratorium. */
  tenureMonths: number;
  /** Repayment holiday in months before the first EMI falls due. */
  moratoriumMonths?: number;
  moratoriumTreatment?: MoratoriumTreatment;
  /** Disbursal date or start date of the loan. */
  startDate?: Date;
};

export type AmortisationRow = {
  month: number;
  dueDate: Date;
  formattedDueDate: string;
  openingBalance: number;
  emi: number;
  interestComponent: number;
  principalComponent: number;
  closingBalance: number;
  /** True for rows inside the moratorium window. */
  isMoratorium: boolean;
};

export type EmiResult = {
  /** Monthly instalment payable after the moratorium ends. */
  emi: number;
  /** Amount actually amortised (principal + capitalised moratorium interest). */
  amortisedPrincipal: number;
  /** Interest accrued during the moratorium window. */
  moratoriumInterest: number;
  /** Interest paid across the repayment period (excludes serviced moratorium interest). */
  totalInterest: number;
  /** Every rupee the borrower parts with, moratorium payments included. */
  totalPayable: number;
  /** Months from disbursement to final instalment. */
  totalMonths: number;
  schedule: AmortisationRow[];
};

const round = (n: number) => Math.round(n);

export function monthlyRate(annualRatePct: number): number {
  return annualRatePct / 12 / 100;
}

/**
 * Standard reducing-balance EMI.
 * EMI = P·r·(1+r)^n / ((1+r)^n − 1), with the r = 0 case handled separately.
 */
export function calculateFlatEmi(principal: number, annualRatePct: number, tenureMonths: number) {
  if (tenureMonths <= 0) throw new RangeError('tenureMonths must be greater than 0');
  if (principal <= 0) return 0;

  const r = monthlyRate(annualRatePct);
  if (r === 0) return principal / tenureMonths;

  const growth = Math.pow(1 + r, tenureMonths);
  return (principal * r * growth) / (growth - 1);
}

/**
 * Full EMI computation including the moratorium behaviour that concessional
 * schemes use (3–12 months, per the problem statement).
 */
export function calculateEmi(input: EmiInput): EmiResult {
  const {
    principal,
    annualRatePct,
    tenureMonths,
    moratoriumMonths = 0,
    moratoriumTreatment = 'CAPITALISE',
    startDate = new Date(),
  } = input;

  if (principal < 0) throw new RangeError('principal cannot be negative');
  if (annualRatePct < 0) throw new RangeError('annualRatePct cannot be negative');
  if (tenureMonths <= 0) throw new RangeError('tenureMonths must be greater than 0');
  if (moratoriumMonths < 0) throw new RangeError('moratoriumMonths cannot be negative');

  const r = monthlyRate(annualRatePct);
  const schedule: AmortisationRow[] = [];
  
  let currentMonthDate = new Date(startDate);

  // --- Moratorium window ---
  let balance = principal;
  let moratoriumInterest = 0;

  for (let m = 1; m <= moratoriumMonths; m += 1) {
    const interest = balance * r;
    moratoriumInterest += interest;

    currentMonthDate.setMonth(currentMonthDate.getMonth() + 1);
    const dueDate = new Date(currentMonthDate);
    const formattedDueDate = dueDate.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

    if (moratoriumTreatment === 'CAPITALISE') {
      const closing = balance + interest;
      schedule.push({
        month: m,
        dueDate,
        formattedDueDate,
        openingBalance: round(balance),
        emi: 0,
        interestComponent: round(interest),
        principalComponent: 0,
        closingBalance: round(closing),
        isMoratorium: true,
      });
      balance = closing;
    } else {
      schedule.push({
        month: m,
        dueDate,
        formattedDueDate,
        openingBalance: round(balance),
        emi: round(interest),
        interestComponent: round(interest),
        principalComponent: 0,
        closingBalance: round(balance),
        isMoratorium: true,
      });
    }
  }

  // --- Repayment window ---
  const amortisedPrincipal = balance;
  const emi = calculateFlatEmi(amortisedPrincipal, annualRatePct, tenureMonths);

  let totalInterest = 0;
  for (let m = 1; m <= tenureMonths; m += 1) {
    const interest = balance * r;
    // Last instalment absorbs float drift so the balance lands exactly on zero.
    const isLast = m === tenureMonths;
    const principalComponent = isLast ? balance : emi - interest;
    const payment = isLast ? balance + interest : emi;
    const closing = isLast ? 0 : balance - principalComponent;

    currentMonthDate.setMonth(currentMonthDate.getMonth() + 1);
    const dueDate = new Date(currentMonthDate);
    const formattedDueDate = dueDate.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

    totalInterest += interest;
    schedule.push({
      month: moratoriumMonths + m,
      dueDate,
      formattedDueDate,
      openingBalance: round(balance),
      emi: round(payment),
      interestComponent: round(interest),
      principalComponent: round(principalComponent),
      closingBalance: round(Math.max(closing, 0)),
      isMoratorium: false,
    });
    balance = Math.max(closing, 0);
  }

  // Derived from the schedule rather than computed separately, so the headline
  // total always equals the instalments the user can see and add up. Summing
  // component figures that were each rounded independently drifts by a few
  // rupees against the schedule, which looks like an error to someone checking.
  //
  // This counts every rupee that leaves the borrower's hands under either
  // treatment: SERVICE_MONTHLY pays the moratorium interest during the holiday
  // (those rows carry an `emi`), while CAPITALISE rolls it into the principal
  // and recovers it through the instalments (those rows carry `emi: 0`).
  const totalPayable = schedule.reduce((sum, row) => sum + row.emi, 0);

  return {
    emi: round(emi),
    amortisedPrincipal: round(amortisedPrincipal),
    moratoriumInterest: round(moratoriumInterest),
    totalInterest: round(totalInterest),
    totalPayable,
    totalMonths: moratoriumMonths + tenureMonths,
    schedule,
  };
}

/**
 * The beneficiary's own contribution — project cost minus the sanctioned loan.
 *
 * Worth surfacing: it is often the reason an application stalls, and a user who
 * only sees "90% funded" can be surprised by the remaining 10% at the branch.
 */
export function marginMoney(projectCost: number, loanAmount: number): number {
  return Math.max(0, projectCost - loanAmount);
}

/**
 * How much loan the applicant can actually get: the lower of the scheme's
 * funding share of the project cost and the scheme's own ceiling.
 */
export function eligibleLoanAmount(
  projectCost: number,
  fundingSharePct: number,
  schemeMaxLoan: number,
): number {
  return Math.max(0, Math.min(Math.floor(projectCost * fundingSharePct), schemeMaxLoan));
}
