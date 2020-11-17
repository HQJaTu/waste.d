import random
from google.cloud import ndb
from waste_d.models import Counter


# from waste_d.models.sql.counter import Counter


class GeneralCounterShardConfig(ndb.Model):
    """Tracks the number of shards for each named counter."""

    SHARD_KEY_TEMPLATE = 'shard-{%s}-{%d}'
    num_shards = ndb.IntegerProperty(default=2)

    @classmethod
    def all_keys(cls, name):
        """Returns all possible keys for the counter name given the config.

        Args:
            name: The name of the counter.

        Returns:
            The full list of ndb.Key values corresponding to all the possible
                counter shards that could exist.
        """
        config = cls.get_or_insert(name)
        shard_key_strings = [GeneralCounterShardConfig.SHARD_KEY_TEMPLATE % (name, index)
                             for index in range(config.num_shards)]
        return [ndb.Key(GeneralCounterShard, shard_key_string)
                for shard_key_string in shard_key_strings]


class GeneralCounterShard(ndb.Model):
    """Shards for each named counter."""
    count = ndb.IntegerProperty(default=0)


def get_count(name):
    """Retrieve the value for a given sharded counter.

    Args:
        name: The name of the counter.

    Returns:
        Integer; the cumulative count of all sharded counters for the given
            counter name.
    """
    total_db = Counter.objects.get(name=name)
    if total_db is None:
        total = 0
        all_keys = GeneralCounterShardConfig.all_keys(name)
        for counter in ndb.get_multi(all_keys):
            if counter is not None:
                total += counter.count

        total_db = Counter(name=name, count=total)
        total_db.save()

    return total_db.count


def increment(name):
    """Increment the value for a given sharded counter.

    Args:
        name: The name of the counter.
    """
    config = GeneralCounterShardConfig.get_or_insert(name)
    return _increment(name, config.num_shards)


@ndb.transactional
def _increment(name, num_shards):
    """Transactional helper to increment the value for a given sharded counter.

    Also takes a number of shards to determine which shard will be used.

    Args:
        name: The name of the counter.
        num_shards: How many shards to use.
    """
    index = random.randint(0, num_shards - 1)
    shard_key_string = GeneralCounterShardConfig.SHARD_KEY_TEMPLATE % (name, index)
    counter = GeneralCounterShard.get_by_id(shard_key_string)
    if counter is None:
        counter = GeneralCounterShard(id=shard_key_string)
    counter.count += 1
    counter.put()

    total_db = Counter.objects.get(name=name)
    new_count = total_db.increment()

    return new_count


@ndb.transactional
def increase_shards(name, num_shards):
    """Increase the number of shards for a given sharded counter.

    Will never decrease the number of shards.

    Args:
        name: The name of the counter.
        num_shards: How many shards to use.
    """
    config = GeneralCounterShardConfig.get_or_insert(name)
    if config.num_shards < num_shards:
        config.num_shards = num_shards
        config.put()
