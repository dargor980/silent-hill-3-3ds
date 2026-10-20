// Own CPU-side adapters; included after the provider's VU/MTGS declarations.
class ObserverVuWorkerPort final : public sh3::observer::WorkerPort
{
public:
	sh3::observer::WorkerControl::Lifecycle lifecycle() const noexcept override
	{
		return vu1Thread.GetObserverLifecycle();
	}
	bool request(Token token) noexcept override { return vu1Thread.RequestObserverControl(token); }
	sh3::observer::WorkerControl::Status status(Token token) const noexcept override
	{
		return vu1Thread.GetObserverStatus(token);
	}
	void release(Token token) noexcept override { vu1Thread.ReleaseObserverControl(token); }
};

class ObserverGsWorkerPort final : public sh3::observer::WorkerPort
{
public:
	sh3::observer::WorkerControl::Lifecycle lifecycle() const noexcept override
	{
		auto value = MTGS::GetObserverLifecycle();
		value.online = value.online && MTGS::IsOpen();
		return value;
	}
	bool request(Token token) noexcept override { return MTGS::RequestObserverControl(token); }
	sh3::observer::WorkerControl::Status status(Token token) const noexcept override
	{
		return MTGS::GetObserverStatus(token);
	}
	void release(Token token) noexcept override { MTGS::ReleaseObserverControl(token); }
};
