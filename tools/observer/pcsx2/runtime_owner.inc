// Own CPU-side state. Included before StopObserverPineDrain, after drain state.
static sh3::observer::RuntimeRevocation s_observer_runtime_ids;
struct ObserverRuntimeOwner final
{
	std::shared_ptr<sh3::observer::RuntimeDiagnosticTicket> ticket;
	sh3::observer::RuntimeDiagnosticSnapshot fixed{};
	bool published = false;
	void revoke(sh3::observer::DiagnosticRejection reason) noexcept
	{
		if (ticket)
			ticket->cancel(reason);
	}
	// Caller has already retired RetainedDrain, including GS/VU/PINE guards.
	void clear() noexcept { if (ticket) ticket->retire(); ticket.reset(); fixed = {}; published = false; }
	~ObserverRuntimeOwner() { revoke(sh3::observer::DiagnosticRejection::lifecycle); }
};
// Destroyed before RetainedDrain: shared historical tickets are already revoked.
static thread_local ObserverRuntimeOwner s_observer_runtime;
