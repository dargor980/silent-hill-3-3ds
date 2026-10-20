// Own integration methods; included after the private provider's declarations.
#include "sh3_observer/runtime_revocation.hpp"
namespace MTGS
{
static sh3::observer::ControlWakeup s_observer_owner_wakeup;
static sh3::observer::WorkerControl s_observer_control{s_observer_owner_wakeup};
static std::uint32_t s_observer_generation = 0; // Worker-owned; persists across sessions.
static bool s_observer_session_online = false; // Worker-only.
static sh3::observer::WorkerControl::Token s_observer_owned{}; // CPU-only.

bool RequestObserverControl(sh3::observer::WorkerControl::Token token)
{
	if (!VMManager::Internal::CanRequestObserverWorker() || s_observer_owned.id ||
		!s_open_flag.load(std::memory_order_acquire) || s_shutdown_flag.load(std::memory_order_acquire) ||
		!s_observer_control.request(token))
		return false;
	s_observer_owned = token;
	s_sem_event.NotifyOfWork();
	return true;
}

bool ReleaseObserverControl(sh3::observer::WorkerControl::Token token)
{
	if (!VMManager::Internal::IsObserverCpuThread() || token != s_observer_owned || !token.id)
		return false;
	sh3::observer::runtime_revocation().advance();
	const bool released = s_observer_control.release(token);
	s_observer_owned = {};
	return released;
}

void CancelObserverControl()
{
	if (VMManager::Internal::IsObserverCpuThread() && s_observer_owned.id)
		ReleaseObserverControl(s_observer_owned);
}

sh3::observer::WorkerControl::Lifecycle GetObserverLifecycle()
{
	return s_observer_control.lifecycle();
}

sh3::observer::WorkerControl::Status GetObserverStatus(sh3::observer::WorkerControl::Token token)
{
	return s_observer_control.status(token);
}

static bool StartObserverControl()
{
	if (s_observer_generation == std::numeric_limits<std::uint32_t>::max())
		return false;
	sh3::observer::runtime_revocation().advance();
	return s_observer_control.start(++s_observer_generation);
}

static void ServiceObserverControl(std::unique_lock<std::mutex>& lock)
{
	const auto token = s_observer_control.pending(s_observer_generation);
	if (!token.id || !s_open_flag.load(std::memory_order_acquire) ||
		s_ReadPos.load(std::memory_order_relaxed) != s_WritePos.load(std::memory_order_acquire) ||
		s_SignalRingEnable.load(std::memory_order_acquire) || s_VsyncSignalListener.load(std::memory_order_acquire))
		return;
	lock.unlock();
	if (s_observer_control.acknowledge(token))
	{
		while (s_observer_control.status(token) == sh3::observer::WorkerControl::Status::held)
			s_observer_control.wait_worker_until(sh3::observer::ControlWakeup::Clock::now() + std::chrono::milliseconds(50));
	}
	lock.lock();
}

static void StopObserverControl()
{
	using Stop = sh3::observer::WorkerControl::StopResult;
	sh3::observer::runtime_revocation().advance();
	for (;;)
	{
		const auto result = s_observer_control.stop(s_observer_generation);
		if (result == Stop::stopped)
			return;
		pxAssert(result != Stop::stale);
		if (result == Stop::retained || result == Stop::stale)
			s_observer_control.wait_worker_until(sh3::observer::ControlWakeup::Clock::now() + std::chrono::milliseconds(50));
	}
}
} // namespace MTGS
