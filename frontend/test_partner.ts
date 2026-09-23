import { PartnerSearchResponseSchema } from './src/api/contracts/partner';
import fs from 'fs';

try {
  const data = JSON.parse(fs.readFileSync('partners.json', 'utf8'));
  const result = PartnerSearchResponseSchema.safeParse(data);
  if (!result.success) {
    console.error("ZOD PARSE FAILED!");
    console.error(JSON.stringify(result.error.issues, null, 2));
  } else {
    console.log("Success! Items:", result.data.items.length);
  }
} catch (e) {
  console.error("Script error:", e);
}
