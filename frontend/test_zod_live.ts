import * as fs from 'fs';
import { SchemeListResponseSchema } from './src/api/contracts/scheme';

const data = JSON.parse(fs.readFileSync('../schemes_resp.json', 'utf8'));
const result = SchemeListResponseSchema.safeParse(data);
if (!result.success) {
  console.log(JSON.stringify(result.error.issues, null, 2));
} else {
  console.log("Success!");
}
