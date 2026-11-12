import { useUi, uiStore } from '../../stores/uiStore';

export default function Toasts() {
  const { toasts } = useUi();
  if (!toasts.length) return null;
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((toast) => (
        <button
          key={toast.id}
          type="button"
          className={`toast toast-${toast.kind}`}
          onClick={() => uiStore.dismiss(toast.id)}
          title="点击关闭"
        >
          <span className="toast-mark" aria-hidden />
          {toast.text}
        </button>
      ))}
    </div>
  );
}
