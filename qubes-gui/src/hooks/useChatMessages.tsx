import { create } from 'zustand';

export interface Message {
  id: string;
  sender: 'user' | 'qube';
  qubeName?: string;
  content: string;
  timestamp: Date;
}

export interface UploadedFile {
  name: string;
  path: string;
  type: 'image' | 'text' | 'pdf' | 'binary';
  data: string;
}

interface ChatMessagesStore {
  // Map of qubeId -> messages
  messagesByQube: Map<string, Message[]>;

  // Map of qubeId -> uploaded files (array)
  uploadedFilesByQube: Map<string, UploadedFile[]>;

  // Get messages for a specific qube
  getMessages: (qubeId: string) => Message[];

  // Add a message for a specific qube
  addMessage: (qubeId: string, message: Message) => void;

  // Clear messages for a specific qube
  clearMessages: (qubeId: string) => void;

  // Clear all messages
  clearAll: () => void;

  // Get uploaded files for a specific qube
  getUploadedFiles: (qubeId: string) => UploadedFile[];

  // Add an uploaded file for a specific qube
  addUploadedFile: (qubeId: string, file: UploadedFile) => void;

  // Remove a specific uploaded file for a qube
  removeUploadedFile: (qubeId: string, fileName: string) => void;

  // Clear all uploaded files for a specific qube
  clearUploadedFiles: (qubeId: string) => void;
}

export const useChatMessages = create<ChatMessagesStore>((set, get) => ({
  messagesByQube: new Map(),
  uploadedFilesByQube: new Map(),

  getMessages: (qubeId: string) => {
    return get().messagesByQube.get(qubeId) || [];
  },

  addMessage: (qubeId: string, message: Message) => {
    set((state) => {
      const newMap = new Map(state.messagesByQube);
      const existingMessages = newMap.get(qubeId) || [];
      newMap.set(qubeId, [...existingMessages, message]);
      return { messagesByQube: newMap };
    });
  },

  clearMessages: (qubeId: string) => {
    set((state) => {
      const newMap = new Map(state.messagesByQube);
      newMap.delete(qubeId);
      return { messagesByQube: newMap };
    });
  },

  clearAll: () => {
    set({ messagesByQube: new Map(), uploadedFilesByQube: new Map() });
  },

  getUploadedFiles: (qubeId: string) => {
    return get().uploadedFilesByQube.get(qubeId) || [];
  },

  addUploadedFile: (qubeId: string, file: UploadedFile) => {
    set((state) => {
      const newMap = new Map(state.uploadedFilesByQube);
      const existingFiles = newMap.get(qubeId) || [];
      newMap.set(qubeId, [...existingFiles, file]);
      return { uploadedFilesByQube: newMap };
    });
  },

  removeUploadedFile: (qubeId: string, fileName: string) => {
    set((state) => {
      const newMap = new Map(state.uploadedFilesByQube);
      const existingFiles = newMap.get(qubeId) || [];
      newMap.set(qubeId, existingFiles.filter(f => f.name !== fileName));
      return { uploadedFilesByQube: newMap };
    });
  },

  clearUploadedFiles: (qubeId: string) => {
    set((state) => {
      const newMap = new Map(state.uploadedFilesByQube);
      newMap.set(qubeId, []);
      return { uploadedFilesByQube: newMap };
    });
  },
}));
