// Own integration methods; included by the private provider after its declarations.
#include "sh3_observer/runtime_revocation.hpp"
bool VU_Thread::RequestObserverControl(sh3::observer::WorkerControl::Token token)
{
	if (!VMManager::Internal::CanRequestObserverWorker() || m_observer_owned.id ||
		m_shutdown_flag.load(std::memory_order_acquire) || !m_observer_control.request(token))
		return false;
	m_observer_owned = token;
	semaEvent.NotifyOfWork();
	return true;
}

bool VU_Thread::ReleaseObserverControl(sh3::observer::WorkerControl::Token token)
{
	if (!VMManager::Internal::IsObserverCpuThread() || token != m_observer_owned || !token.id)
		return false;
	sh3::observer::runtime_revocation().advance();
	const bool released = m_observer_control.release(token);
	m_observer_owned = {};
	return released;
}

void VU_Thread::CancelObserverControl()
{
	if (VMManager::Internal::IsObserverCpuThread() && m_observer_owned.id)
		ReleaseObserverControl(m_observer_owned);
}

sh3::observer::WorkerControl::Lifecycle VU_Thread::GetObserverLifecycle() const
{
	return m_observer_control.lifecycle();
}

sh3::observer::WorkerControl::Status VU_Thread::GetObserverStatus(sh3::observer::WorkerControl::Token token) const
{
	return m_observer_control.status(token);
}

bool VU_Thread::StartObserverControl()
{
	if (m_observer_generation == std::numeric_limits<std::uint32_t>::max())
		return false;
	sh3::observer::runtime_revocation().advance();
	return m_observer_control.start(++m_observer_generation);
}

void VU_Thread::ServiceObserverControl()
{
	const auto token = m_observer_control.pending(m_observer_generation);
	// Acquire the request before rechecking the queue: the previous empty test
	// may precede a CPU publication and its subsequent control request.
	if (!token.id || m_ato_read_pos.load(std::memory_order_relaxed) != GetWritePos() ||
		!m_observer_control.acknowledge(token))
		return;
	while (m_observer_control.status(token) == sh3::observer::WorkerControl::Status::held)
		m_observer_control.wait_worker_until(sh3::observer::ControlWakeup::Clock::now() + std::chrono::milliseconds(50));
}

void VU_Thread::StopObserverControl()
{
	using Stop = sh3::observer::WorkerControl::StopResult;
	sh3::observer::runtime_revocation().advance();
	for (;;)
	{
		const auto result = m_observer_control.stop(m_observer_generation);
		if (result == Stop::stopped)
			return;
		// A stale generation is impossible with one worker and monotonically increasing life.
		pxAssert(result != Stop::stale);
		if (result == Stop::retained || result == Stop::stale)
			m_observer_control.wait_worker_until(sh3::observer::ControlWakeup::Clock::now() + std::chrono::milliseconds(50));
	}
}
