import { FeedbackReviewQueuePage } from "./queue.js";

export default function FeedbackPage() {
  return <FeedbackReviewQueuePage apiBaseUrl={process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"} />;
}
