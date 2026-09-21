"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Button, Badge, Spinner } from "@/components/ui";
import { Send, Mic, MicOff, Paperclip, X, FileText, Upload } from "lucide-react";
import Image from "next/image";
import { toast } from "sonner";
import { uploadFile, getFileUrl, type FileUploadResponse } from "@/lib/file-api";
import { getErrorMessage, MAX_UPLOAD_SIZE_MB } from "@/lib/utils";
import {
  BUILTIN_COMMANDS,
  searchCommands,
  type SlashCommand,
  type SlashCommandContext,
} from "./slash-commands";
import { SlashCommandPalette } from "./slash-command-palette";

interface ChatInputProps {
  onSend: (message: string, fileIds?: string[], files?: FileUploadResponse[]) => void;
  disabled?: boolean;
  isProcessing?: boolean;
  /** When set, a stop control replaces the send button while processing. */
  onStop?: () => void;
  /** Local actions for slash commands. Wire from <ChatContainer>. */
  slashContext?: SlashCommandContext;
  /** Effective slash commands (built-ins + user customs, after overrides). */
  commands?: SlashCommand[];
}

export function ChatInput({
  onSend,
  disabled,
  isProcessing,
  onStop,
  slashContext,
  commands,
}: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<FileUploadResponse[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  // Slash-command palette state. Open while message starts with "/" and the
  // caller wired a context — without one, commands have nothing to do.
  const [paletteIndex, setPaletteIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const ignoreSpeechResultsRef = useRef(false);

  const showPalette = !!slashContext && message.startsWith("/") && !message.includes("\n");
  const allCommands = commands ?? BUILTIN_COMMANDS;
  const filteredCommands = useMemo(
    () => (showPalette ? searchCommands(allCommands, message) : []),
    [showPalette, message, allCommands],
  );

  useEffect(() => {
    setPaletteIndex(0);
  }, [filteredCommands.length, message]);

  useEffect(() => {
    if (!isProcessing && !isUploading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isProcessing, isUploading]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

  const runSlashCommand = useCallback(
    (cmd: SlashCommand) => {
      if (cmd.action.kind === "client") {
        cmd.action.run(slashContext!);
        setMessage("");
        return;
      }
      // send-as-message — replace the slash with the canned prompt and send
      // through the normal flow so it lands as a regular user turn.
      const fileIds = attachedFiles.length > 0 ? attachedFiles.map((f) => f.id) : undefined;
      const files = attachedFiles.length > 0 ? attachedFiles : undefined;
      ignoreSpeechResultsRef.current = true;
      recognitionRef.current?.abort();
      setIsListening(false);
      onSend(cmd.action.replaceWith, fileIds, files);
      setMessage("");
      setAttachedFiles([]);
    },
    [attachedFiles, onSend, slashContext],
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (showPalette && filteredCommands[paletteIndex]) {
      runSlashCommand(filteredCommands[paletteIndex]);
      return;
    }
    const trimmed = message.trim();
    if (!trimmed && attachedFiles.length === 0) return;
    if (disabled || isUploading) return;

    const fileIds = attachedFiles.length > 0 ? attachedFiles.map((f) => f.id) : undefined;
    const files = attachedFiles.length > 0 ? attachedFiles : undefined;
    ignoreSpeechResultsRef.current = true;
    recognitionRef.current?.abort();
    setIsListening(false);
    onSend(trimmed || "Analyze the attached file(s)", fileIds, files);
    setMessage("");
    setAttachedFiles([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showPalette && filteredCommands.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setPaletteIndex((i) => (i + 1) % filteredCommands.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setPaletteIndex((i) => (i - 1 + filteredCommands.length) % filteredCommands.length);
        return;
      }
      if (e.key === "Tab") {
        // Tab autocompletes to the highlighted command name.
        e.preventDefault();
        const cmd = filteredCommands[paletteIndex];
        if (cmd) setMessage("/" + cmd.name + " ");
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        setMessage("");
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const toggleMic = useCallback(async () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      toast.info("Voice input is only supported in Chrome. Use Chrome for speech-to-text.");
      return;
    }

    let micPreflightSucceeded = false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micPreflightSucceeded = true;
      stream.getTracks().forEach((track) => track.stop());
    } catch (err) {
      setIsListening(false);
      const errorName = err instanceof DOMException ? err.name : "";
      if (errorName === "NotAllowedError" || errorName === "PermissionDeniedError") {
        toast.error(
          "Chrome or macOS is blocking microphone input. Reset the site permission, then check System Settings > Privacy & Security > Microphone for Chrome.",
        );
        return;
      }
      if (errorName === "NotFoundError" || errorName === "DevicesNotFoundError") {
        toast.error("No microphone was found. Check your Mac input device settings.");
        return;
      }
      toast.error(getErrorMessage(err, "Could not access the microphone"));
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = navigator.language || "en-US";

    let finalTranscript = "";
    let wasAborted = false;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      if (ignoreSpeechResultsRef.current) return;
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (!result) continue;
        if (result.isFinal) {
          finalTranscript += result[0]?.transcript ?? "";
        } else {
          interim += result[0]?.transcript ?? "";
        }
      }
      setMessage(() => {
        return finalTranscript + (interim ? "\u200B" + interim : "");
      });
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      setIsListening(false);
      if (ignoreSpeechResultsRef.current) {
        ignoreSpeechResultsRef.current = false;
        return;
      }
      setMessage((prev) => prev.replace(/\u200B/g, ""));
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (ignoreSpeechResultsRef.current) {
        recognitionRef.current = null;
        setIsListening(false);
        ignoreSpeechResultsRef.current = false;
        return;
      }
      wasAborted = event.error === "aborted";
      recognitionRef.current = null;
      setIsListening(false);
      if (wasAborted) return;

      const messageByError: Partial<Record<SpeechRecognitionErrorEvent["error"], string>> = {
        "audio-capture":
          "No microphone was found. Check your Mac and Chrome microphone settings.",
        "language-not-supported": "Speech recognition does not support this language.",
        network: "Speech recognition could not reach Chrome's speech service. Try again shortly.",
        "no-speech": "I didn't catch any speech. Try again and speak after the mic activates.",
        "not-allowed": micPreflightSucceeded
          ? "Chrome allowed the mic but blocked speech recognition. Reset the site permission or try the app over HTTPS."
          : "Microphone access is blocked. Allow microphone access for this site.",
        "service-not-allowed":
          "Chrome blocked the speech recognition service. Check site permissions and try again.",
      };
      toast.error(messageByError[event.error] ?? `Speech recognition error: ${event.error}`);
    };

    recognitionRef.current = recognition;
    finalTranscript = message;
    ignoreSpeechResultsRef.current = false;
    try {
      recognition.start();
      setIsListening(true);
    } catch (err) {
      recognitionRef.current = null;
      setIsListening(false);
      toast.error(getErrorMessage(err, "Could not start speech recognition"));
    }
  }, [isListening, message]);

  // File upload to backend — shared by the file picker and drag-and-drop.
  const uploadFiles = useCallback(async (files: File[]) => {
    if (files.length === 0) return;
    for (const file of files) {
      if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
        toast.error(`${file.name}: File too large. Maximum ${MAX_UPLOAD_SIZE_MB}MB.`);
        continue;
      }

      setIsUploading(true);
      try {
        const result = await uploadFile(file);
        setAttachedFiles((prev) => [...prev, result]);
      } catch (err) {
        toast.error(`${file.name}: ${getErrorMessage(err, "Upload failed")}`);
      } finally {
        setIsUploading(false);
      }
    }
  }, []);

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []);
      if (files.length === 0) return;
      e.target.value = "";
      await uploadFiles(files);
    },
    [uploadFiles],
  );

  // Drag-and-drop files anywhere onto the composer. A counter handles nested
  // dragenter/dragleave so the overlay doesn't flicker over child elements.
  const [isDragging, setIsDragging] = useState(false);
  const dragDepth = useRef(0);
  const isFileDrag = (e: React.DragEvent) => Array.from(e.dataTransfer.types).includes("Files");
  const handleDragEnter = (e: React.DragEvent) => {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    dragDepth.current += 1;
    setIsDragging(true);
  };
  const handleDragOver = (e: React.DragEvent) => {
    if (isFileDrag(e)) e.preventDefault();
  };
  const handleDragLeave = (e: React.DragEvent) => {
    if (!isFileDrag(e)) return;
    dragDepth.current -= 1;
    if (dragDepth.current <= 0) {
      dragDepth.current = 0;
      setIsDragging(false);
    }
  };
  const handleDrop = (e: React.DragEvent) => {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    dragDepth.current = 0;
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) void uploadFiles(files);
  };

  const removeFile = (fileId: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="relative"
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="border-foreground/40 bg-card/95 text-foreground absolute inset-0 z-30 flex items-center justify-center rounded-2xl border-2 border-dashed text-sm font-medium backdrop-blur-sm">
          <span className="flex items-center gap-2">
            <Upload className="h-4 w-4" /> Drop files to attach
          </span>
        </div>
      )}
      {showPalette && (
        <SlashCommandPalette
          commands={filteredCommands}
          selectedIndex={paletteIndex}
          onSelectIndex={setPaletteIndex}
          onPick={runSlashCommand}
        />
      )}
      {(attachedFiles.length > 0 || isUploading) && (
        <div className="flex flex-wrap items-center gap-2 pb-2">
          {attachedFiles.map((file) => (
            <div key={file.id} className="relative">
              {file.file_type === "image" ? (
                <div className="group relative h-16 w-16 overflow-hidden rounded-lg border">
                  <Image
                    src={getFileUrl(file.id)}
                    alt={file.filename}
                    fill
                    className="object-cover"
                    unoptimized
                  />
                  <button
                    type="button"
                    onClick={() => removeFile(file.id)}
                    className="bg-destructive text-destructive-foreground absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ) : (
                <Badge variant="secondary" className="gap-1.5 pr-1">
                  <FileText className="h-3 w-3" />
                  <span className="max-w-[150px] truncate text-xs">{file.filename}</span>
                  <button
                    type="button"
                    onClick={() => removeFile(file.id)}
                    className="hover:bg-muted ml-0.5 rounded p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )}
            </div>
          ))}
          {isUploading && (
            <div className="flex h-16 w-16 items-center justify-center rounded-lg border border-dashed">
              <Spinner className="text-muted-foreground h-5 w-5" />
            </div>
          )}
        </div>
      )}

      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={disabled}
          rows={1}
          className="placeholder:text-muted-foreground min-h-[40px] flex-1 resize-none scrollbar-thin bg-transparent py-2.5 text-sm focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 sm:text-base"
        />

        <div className="flex shrink-0 items-center gap-0.5 pb-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={toggleMic}
            disabled={disabled}
            className="h-9 w-9"
            title={isListening ? "Stop recording" : "Voice input"}
            aria-label={isListening ? "Stop recording" : "Voice input"}
          >
            {isListening ? (
              <MicOff className="h-4 w-4 animate-pulse text-red-500" />
            ) : (
              <Mic className="text-muted-foreground h-4 w-4" />
            )}
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading}
            className="h-9 w-9"
            title="Attach file"
            aria-label="Attach file"
          >
            {isUploading ? (
              <Spinner className="text-muted-foreground h-4 w-4" />
            ) : (
              <Paperclip className="text-muted-foreground h-4 w-4" />
            )}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            accept="image/jpeg,image/png,image/gif,image/webp,.txt,.md,.csv,.json,.py,.js,.ts,.tsx,.html,.css,.yaml,.yml,.toml,.xml,.sql,.sh,.pdf,.docx"
            multiple
            className="hidden"
          />

          {isProcessing && onStop ? (
            <Button
              type="button"
              size="icon"
              onClick={onStop}
              className="h-9 w-9 rounded-lg"
              title="Stop generating"
            >
              <span className="h-3 w-3 rounded-[3px] bg-current" aria-hidden="true" />
              <span className="sr-only">Stop generating</span>
            </Button>
          ) : (
            <Button
              type="submit"
              size="icon"
              disabled={disabled || isUploading || (!message.trim() && attachedFiles.length === 0)}
              className="h-9 w-9 rounded-lg"
            >
              {isProcessing ? <Spinner className="h-4 w-4" /> : <Send className="h-4 w-4" />}
              <span className="sr-only">Send message</span>
            </Button>
          )}
        </div>
      </div>
    </form>
  );
}
