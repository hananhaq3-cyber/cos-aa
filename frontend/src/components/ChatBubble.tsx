/**
 * Chat message bubble component.
 */
import clsx from "clsx";

interface ChatBubbleProps {
  role: string;
  content: string;
  timestamp?: string;
}

export default function ChatBubble({
  role,
  content,
  timestamp,
}: ChatBubbleProps) {
  const isUser = role === "USER" || role === "user";

  return (
    <div
      className={clsx("flex mb-4", isUser ? "justify-end" : "justify-start")}
    >
      <div
        className={clsx(
          "max-w-[70%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-primary-600 text-white rounded-br-md"
            : "bg-gray-800 text-gray-200 rounded-bl-md"
        )}
      >
        <p className="whitespace-pre-wrap">{content}</p>
        {timestamp && (
          <p
            className={clsx(
              "text-xs mt-1",
              isUser ? "text-primary-200" : "text-gray-500"
            )}
          >
            {new Date(timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  );
}
