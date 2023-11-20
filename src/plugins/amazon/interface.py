import asyncio
from .backend import backend


class SubscribeManager:

    def subscribe(self, group_id: str, params: list[str]):
        """
        命令格式: 愿望单关注 名称 LID [推送途径 推送目的地]
        """
        if len(params) < 3:
            return self.subscribe.__doc__.strip()

        name = params[1]
        lid = params[2]
        notice_type = 'group'
        push_to = group_id

        if len(params) >= 5:
            notice_type = params[3]
            push_to = params[4]

        return backend.subscribe(
            _user_id=group_id,
            _name=name,
            _lid=lid,
            _notice_type=notice_type,
            _push_to=push_to,
        )

    def unsubscribe(self, params: list[str]):
        """
        命令格式: 愿望单取关 名称|LID
        """

        if len(params) < 2:
            return self.unsubscribe.__doc__.strip()

        if backend.unsubscribe_by_lid(params[1]):
            return '取关成功'

        if backend.unsubscribe_by_name(params[1]):
            return '取关成功'

        return '没有找到对应订阅'

    @staticmethod
    def query(group_id: str):
        return backend.query_sub(group_id)

    @staticmethod
    def create_requests():
        subscriptions = backend.select_targets()

        tasks = []

        for subscription in subscriptions:
            tasks.append(asyncio.create_task(backend.request(subscription.target)))

        return tasks

    @staticmethod
    def create_notifications(resp: list[str]):
        tasks = []

        for lid, text in resp:

            new_commodities = backend.parse_resp(text)

            if new_commodities is None:
                continue

            old_commodities = set()

            for commodity in backend.select_commodities(lid):
                old_commodities.add(commodity.name)

            add_commodities = new_commodities.difference(old_commodities)
            delete_commodities = old_commodities.difference(new_commodities)

            message = backend.build_message(add_commodities, delete_commodities, lid)

            for subscription in backend.select_notices(lid):
                tasks.append((subscription.notice_id, message, ))

        return tasks


manager = SubscribeManager()
