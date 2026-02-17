import { cn } from "@/lib/utils";

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
}

export function MessageList({ messages, isStreaming }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground text-sm">
        Send a message to start chatting with your selected AI model.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 py-4">
      {messages.map((message, index) => (
        <div
          key={index}
          className={cn(
            "flex",
            message.role === "user" ? "justify-end" : "justify-start"
          )}
        >
          <div
            className={cn(
              "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
              message.role === "user"
                ? "bg-primary text-primary-foreground rounded-br-sm"
                : "bg-muted text-foreground rounded-bl-sm"
            )}
          >
            {message.content}
            {isStreaming &&
              index === messages.length - 1 &&
              message.role === "assistant" && (
                <span className="ml-1 inline-block h-4 w-0.5 animate-pulse bg-current opacity-70" />
              )}
          </div>
        </div>
      ))}
    </div>
  );
}
