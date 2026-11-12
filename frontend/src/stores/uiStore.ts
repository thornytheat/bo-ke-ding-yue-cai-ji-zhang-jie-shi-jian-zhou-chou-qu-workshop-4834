/** UI store：toast 队列 + 跨页保持的筛选上下文（采集 → 异常队列不迷路）。 */
import { useSyncExternalStore } from 'react';

export interface Toast {
  id: number;
  text: string;
  kind: 'ok' | 'bad' | 'info';
}

interface UiState {
  toasts: Toast[];
  feedFilter: string;
  issueKindFilter: string;
  lastTaskCode: string | null;
}

type Listener = () => void;

class UiStore {
  private state: UiState = { toasts: [], feedFilter: '', issueKindFilter: '', lastTaskCode: null };
  private listeners = new Set<Listener>();
  private seq = 0;

  subscribe = (listener: Listener) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getState = (): UiState => this.state;

  private emit(next: Partial<UiState>) {
    this.state = { ...this.state, ...next };
    this.listeners.forEach((listener) => listener());
  }

  toast(text: string, kind: Toast['kind'] = 'ok') {
    const id = ++this.seq;
    this.emit({ toasts: [...this.state.toasts, { id, text, kind }] });
    window.setTimeout(() => this.dismiss(id), 4200);
  }

  dismiss(id: number) {
    this.emit({ toasts: this.state.toasts.filter((item) => item.id !== id) });
  }

  setFeedFilter(feedFilter: string) {
    this.emit({ feedFilter });
  }

  setIssueKindFilter(issueKindFilter: string) {
    this.emit({ issueKindFilter });
  }

  setLastTask(code: string | null) {
    this.emit({ lastTaskCode: code });
  }
}

export const uiStore = new UiStore();

export function useUi() {
  return useSyncExternalStore(uiStore.subscribe, uiStore.getState);
}
