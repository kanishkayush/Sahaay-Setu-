import { AssistantQueryResponseSchema } from './src/api/contracts/assistant';

const payload = {
  "messageId":"08bf8915-3726-45ad-ae9a-f7692ddcc60f",
  "answer":"Information related to your query:\n\n• Term Loan Scheme\n• Educational Loan Scheme\n\nPlease refer to the official scheme documentation for more details.",
  "answerLanguage":"en",
  "detectedQueryLanguage":"en",
  "citations":[
    {"id":"NSFDC_OFFICIAL_WEBSITE","title":"NSFDC_OFFICIAL_WEBSITE","locator":"overview","url":null,"snippet":null,"confidence":null},
    {"id":"NSFDC_OFFICIAL_WEBSITE","title":"NSFDC_OFFICIAL_WEBSITE","locator":"financial_terms","url":null,"snippet":null,"confidence":null}
  ],
  "suggestedActions":[],
  "followUpQuestions":[],
  "grounded":true,
  "sessionId":"test-session"
};

const result = AssistantQueryResponseSchema.safeParse(payload);
if (result.success) {
  console.log("PASS");
} else {
  console.log("FAIL", JSON.stringify(result.error.issues, null, 2));
}
