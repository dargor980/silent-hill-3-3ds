// Own integration methods; provider symbols are declared by VMManager.
std::shared_ptr<sh3::observer::RuntimeDiagnosticTicket> VMManager::Internal::QueueObserverRuntimeDiagnostic(
	u64 id, std::chrono::milliseconds timeout)
{
	if (timeout <= std::chrono::milliseconds::zero() || timeout > std::chrono::seconds(5))
		return {};
	return QueueObserverRuntimeDiagnosticUntil(id, sh3::observer::PineDrain::Clock::now() + timeout);
}

std::shared_ptr<sh3::observer::RuntimeDiagnosticTicket> VMManager::Internal::QueueObserverRuntimeDiagnosticUntil(
	u64 id, sh3::observer::PineDrain::Clock::time_point deadline)
{
	using namespace sh3::observer;
	const auto now = PineDrain::Clock::now();
	if (!s_observer_cpu_thread || s_observer_external_waits.pending() || s_observer_pine_drain.active() ||
		s_observer_runtime.ticket || GetState() != VMState::Paused || !id || id == UINT64_MAX ||
		deadline <= now || now > PineDrain::Clock::time_point::max() - std::chrono::seconds(5) ||
		deadline > now + std::chrono::seconds(5))
		return {};
	const auto scope = s_observer_runtime_ids.advance();
	if (!scope || scope == UINT64_MAX)
		return {};
	auto ticket = make_runtime_diagnostic_ticket(runtime_revocation());
	if (!ticket)
		return {};
	const PineDrain::Identity identity{host_epoch(), PINEServer::GetObserverGeneration()};
	if (!s_observer_pine_drain.submit({id, identity, deadline}))
		return {};
	s_observer_runtime.fixed.scope_id = scope;
	s_observer_runtime.fixed.deadline = deadline;
	s_observer_runtime.ticket = ticket;
	Host::WakeObserverPineDrain();
	return ticket;
}

static bool UpdateObserverRuntimeDiagnostic()
{
	using namespace sh3::observer;
	if (!s_observer_runtime.ticket || s_observer_pine_drain.status().state != PineDrain::State::held)
		return false;
	const auto sample = [] {
		auto value = s_observer_runtime.fixed;
		const auto vu = s_observer_vu_port.lifecycle();
		const auto gs = s_observer_gs_port.lifecycle();
		value.epochs = {host_epoch(), PINEServer::GetObserverGeneration(),
			vu.online ? vu.generation : 0, gs.online ? gs.generation : 0};
		value.facts = VMManager::Internal::SampleObserverAdmissionProfile();
		// These facts come from this retained attempt, not configuration flags.
		for (auto key : {AdmissionCondition::pine_excluded, AdmissionCondition::vu_drained, AdmissionCondition::gs_drained})
			value.facts[static_cast<std::size_t>(key)] = AdmissionFact::satisfied;
		return value;
	};
	const auto before = sample();
	if (s_observer_pine_drain.step(VMManager::GetState() == VMState::Paused,
		{host_epoch(), PINEServer::GetObserverGeneration()}) != PineDrain::State::held)
		return false;
	const auto after = sample();
	if (before.epochs.host != after.epochs.host || before.epochs.pine != after.epochs.pine ||
		before.epochs.vu != after.epochs.vu || before.epochs.gs != after.epochs.gs || before.facts != after.facts)
		return false;
	if (s_observer_runtime.published)
		return s_observer_runtime.ticket->revalidate(after);
	if (!s_observer_runtime.ticket->publish(after))
		return false;
	s_observer_runtime.published = true;
	return true;
}
