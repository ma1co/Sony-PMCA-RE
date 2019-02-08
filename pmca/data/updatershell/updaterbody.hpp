#pragma once
#include "updater/updaterbody.hpp"

class UpdaterBodyImpl : public Updater::UpdaterBody
{
public:
    virtual ~UpdaterBodyImpl() {}
    virtual bool Execute(Updater::RingBuffer *buffer, Updater::CallbackInterface *interface);
    virtual void Stop() {}
};
